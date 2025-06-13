import concurrent.futures
import re
import math
from typing import Any, Dict, List, Optional
from request_api import *

# Évite les noms peu exploitables (métadonnées, structures de surface)
def is_bad_name(name: str) -> bool:
    bad_substrings = [":", "en"]
    return any(sub in name for sub in bad_substrings) or name.startswith("_")



# Filtre les relations pertinentes d’un nœud selon un sens (from/to) et une liste de relations attendues
def get_filtered_relations(node, direction, patterns):
    all_relations = get_relations_to(node) if direction == "to" else get_relations_from(node)
    if not all_relations:
        return {}

    # Filtrage initial sur le poids et le type de relation
    filtered_rels = [
        rel for rel in all_relations.get("relations", [])
        if abs(rel["w"]) >= 5 and (rel_name := get_relation_name(rel["type"])) in patterns
    ]

    # On ne charge que les nœuds concernés
    all_ids = {
        rel["node1"] if direction == "to" else rel["node2"]
        for rel in filtered_rels
    }
    preload_nodes_by_id_parallel(list(all_ids))

    # On trie ensuite les relations conservées avec un dictionnaire par nœud
    relations_dict = {}
    for rel in filtered_rels:
        intermediate_node_id = rel["node1"] if direction == "to" else rel["node2"]
        intermediate_node = get_node_by_id(intermediate_node_id)
        if not intermediate_node:
            continue
        if is_bad_name(intermediate_node.get("name", "")):
            continue

        if intermediate_node_id not in relations_dict:
            relations_dict[intermediate_node_id] = []
        relations_dict[intermediate_node_id].append(rel)

    # Limite le nombre de relations retenues par nœud intermédiaire (50 max)
    for node_id in relations_dict:
        relations_dict[node_id] = sorted(
            relations_dict[node_id],
            key=lambda r: abs(r["w"]),
            reverse=True
        )[:50]

    return relations_dict



# Tente une inférence logique à travers un nœud intermédiaire
def process_intermediate_node(rel1, node1, node2, relations_to_dict, relation, valid_patterns):
    intermediate_node = get_node_by_id(rel1["node2"])
    if not intermediate_node:
        return None

    intermediate_name = intermediate_node.get("name", "")
    weight1 = rel1["w"]
    relations_to = relations_to_dict.get(intermediate_node["id"], [])
    local_results = []

    for rel2 in relations_to:
        r1_name = get_relation_name(rel1["type"])
        r2_name = get_relation_name(rel2["type"])
        if (r1_name, r2_name) not in valid_patterns:
            continue

        weight2 = rel2["w"]
        # Relation r_associated moins fiable donc on pénalise le poids
        if r1_name == "r_associated":
            weight1 /= 4
        if r2_name == "r_associated":
            weight2 /= 4

        combined_weight = math.sqrt(abs(weight1 * weight2))
        rel_neg = weight1 * weight2 < 0

        local_results.append([
            node1, rel1['type'], intermediate_name, rel2['type'], node2,
            relation, rel_neg, f"{combined_weight:.2f}", f"{weight1}", f"{weight2}"
        ])

    return local_results

# Exécute toutes les inférences possibles à partir des relations filtrées
def explore_intermediate_relations(node1, node2, relations_from_dict, relations_to_dict, relation, valid_patterns):
    results = []
    all_relations_from = [rel for rels in relations_from_dict.values() for rel in rels]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_rel = {
            executor.submit(process_intermediate_node, rel1, node1, node2, relations_to_dict, relation, valid_patterns): rel1
            for rel1 in all_relations_from
        }
        for future in concurrent.futures.as_completed(future_to_rel):
            result = future.result()
            if result:
                results.extend(result)
    # Trie les résultats par poids, en minorant les inférences négatives
    results.sort(key=lambda x: float(x[-1]) * (0.75 if x[6] else 1), reverse=True)
    return results



# Formate un résultat d’inférence de manière lisible
def format_inference(idx, result):
    rel1_name = get_relation_name(result[1])
    rel2_name = get_relation_name(result[3])
    weight1 = result[7]
    rel_neg = result[6]

    neg = "non" if rel_neg else "oui"
    explanation = f"{result[0]} {rel1_name} {result[2]} & {result[2]} {rel2_name} {result[4]}"
    explanation += f" (poids r1={result[8]}, r2={result[9]})"

    return f"{idx} | {neg} | {explanation} | {weight1}"

# Analyse les résultats pour proposer une conclusion globale (oui, non ou incertain)
def summarize_inference_results(results: List[str], node1: str, relation: str, node2: str) -> str:
    top_results = results[:10]
    positives = [r for r in top_results if "| oui |" in r]
    negatives = [r for r in top_results if "| non |" in r]

    def extract_score(r):
        match = re.findall(r"\|\s?([\d.]+)$", r)
        return float(match[0]) if match else 0.0

    pos_scores = [extract_score(r) for r in positives]
    neg_scores = [extract_score(r) for r in negatives]
    score_diff = sum(pos_scores) - sum(neg_scores)

    summary = "\n---\n"
    if score_diff > 0 and len(positives) >= len(negatives):
        summary += (
            f"✅ Conclusion : il est probable que '{node1}' {relation} '{node2}'\n"
            f"   ✔ {len(positives)} oui (score total : {sum(pos_scores):.1f})\n"
            f"   ✖ {len(negatives)} non (score total : {sum(neg_scores):.1f})"
        )
    elif score_diff < 0 and len(negatives) >= len(positives):
        summary += (
            f"❌ Conclusion : il est improbable que '{node1}' {relation} '{node2}'\n"
            f"   ✔ {len(positives)} oui (score total : {sum(pos_scores):.1f})\n"
            f"   ✖ {len(negatives)} non (score total : {sum(neg_scores):.1f})"
        )
    else:
        summary += (
            f"❓ Conclusion : incertain pour '{node1}' {relation} '{node2}'\n"
            f"   ✔ {len(positives)} oui (score total : {sum(pos_scores):.1f})\n"
            f"   ✖ {len(negatives)} non (score total : {sum(neg_scores):.1f})"
        )

    return summary



# Fonction principale qui exécute les inférences entre deux mots via une relation
def infer_relation(node1: str, relation: str, node2: str) -> List[str]:
    results = []
    print(f"[INFÉRENCE] Début pour : {node1} {relation} {node2}")
    relation_id = get_relation_id(relation)
    if relation_id is None:
        return [f"Relation '{relation}' inconnue"]

    print("[DIRECT] Recherche de relation directe...")
    direct_relations = get_relations_between(node1, node2)
    if direct_relations:
        for rel in direct_relations.get("relations", []):
            if rel["type"] == relation_id:
                print(f"[DIRECT] Relation directe trouvée avec poids {rel['w']}")
                results.append(f"1 | oui | {node1} {relation} {node2} (relation directe) | {rel['w']}")

    inference_patterns = load_inference_patterns()
    patterns_to_check = inference_patterns.get(relation, []) + inference_patterns.get("R", []) + inference_patterns.get("default", [])

    valid_patterns = [(p[0], p[1] if p[1] != "R" else relation) for p in patterns_to_check if len(p) == 2]
    patterns1 = list(dict.fromkeys([p[0] for p in valid_patterns]))
    patterns2 = list(dict.fromkeys([p[1] for p in valid_patterns]))

    print("[FILTRE] Chargement des relations sortantes de", node1)
    relations_from_dict = get_filtered_relations(node1, "from", patterns1)
    print("[FILTRE] Chargement des relations entrantes vers", node2)
    relations_to_dict = get_filtered_relations(node2, "to", patterns2)

    print("[INFÉRENCE] Exploration des relations intermédiaires...")
    infer_res = explore_intermediate_relations(node1, node2, relations_from_dict, relations_to_dict, relation, valid_patterns)
    results += [format_inference(i + 1, r) for i, r in enumerate(infer_res)]
    print(f"[INFÉRENCE] {len(results)} inférences explorées")

    if not results:
        return [f"Aucune inférence trouvée pour {node1} {relation} {node2}."]

    results.sort(
        key=lambda s: float(re.findall(r"\|\s?([\d.]+)$", s)[0]) if re.findall(r"\|\s?([\d.]+)$", s) else 0,
        reverse=True
    )

    summary = summarize_inference_results(results, node1, relation, node2)
    print(f"[FIN] {summary}")
    return results[:10] + [summary]
