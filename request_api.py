import requests
import os
import json
import concurrent.futures
from tqdm import tqdm
from typing import Any, Dict, List, Optional

BASE_URL = "https://jdm-api.demo.lirmm.fr/v0"
CACHE_DIR = "cache"

relation_types = {}
inference_patterns = {}
node_cache = {}  # cache en memoire pour node_by_id



# Nettoie un nom pour le rendre compatible avec le système de fichiers
def sanitize_filename(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_").replace(":", "_")

# Récupère la réponse d'un endpoint, avec mise en cache locale (évite les requêtes répétées)
def get_cached_response(endpoint: str) -> Optional[Dict[str, Any]]:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{sanitize_filename(endpoint)}.json")

    # Si le fichier est déjà en cache, le charger
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            os.remove(cache_file)  # Si le fichier est corrompu, on le supprime

    # Sinon, envoyer une requête à l'API
    response = get_json_response(f"{BASE_URL}/{endpoint}")
    if response:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=4)
        except Exception:
            pass

    return response

# Effectue une requête GET et renvoie le JSON ou None si erreur
def get_json_response(url: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None



# Retourne un nœud par ID avec mise en cache mémoire
def get_node_by_id(node_id: int) -> Optional[Dict[str, Any]]:
    if node_id in node_cache:
        return node_cache[node_id]
    node = get_cached_response(f"node_by_id/{node_id}")
    if node:
        node_cache[node_id] = node
    return node

# Recherche un nœud par son nom
def get_node_by_name(node_name: str) -> Optional[Dict[str, Any]]:
    return get_cached_response(f"node_by_name/{node_name}")

# Récupère les raffinements d'un mot (polysémie, spécialisations...)
def get_refinements(node_name: str) -> Optional[List[Dict[str, Any]]]:
    return get_cached_response(f"refinements/{node_name}")

# Récupère la liste des types de nœuds et relations
def get_nodes_types() -> Optional[List[Dict[str, Any]]]:
    return get_cached_response("nodes_types")

def get_relations_types() -> Optional[List[Dict[str, Any]]]:
    return get_cached_response("relations_types")

# Conversion entre nom et ID de relation
def get_relation_id(relation_name: str) -> Optional[int]:
    data = get_relations_types()
    if not data:
        return None
    for relation in data:
        if relation["name"] == relation_name:
            return relation["id"]
    return None

def get_relation_name(relation_id: int) -> Optional[str]:
    data = get_relations_types()
    if not data:
        return None
    for relation in data:
        if relation["id"] == relation_id:
            return relation["name"]
    return None



# Récupère toutes les relations sortantes du nœud
def get_relations_from(node1_name: str) -> Optional[Dict[str, Any]]:
    return get_cached_response(f"relations/from/{node1_name}")

# Récupère les relations directes entre deux nœuds
def get_relations_between(node1_name: str, node2_name: str) -> Optional[Dict[str, Any]]:
    return get_cached_response(f"relations/from/{node1_name}/to/{node2_name}")

# Récupère toutes les relations entrantes vers un nœud
def get_relations_to(node2_name: str) -> Optional[Dict[str, Any]]:
    return get_cached_response(f"relations/to/{node2_name}")



# Charge les schémas d’inférence depuis inference_patterns.JSON
def load_inference_patterns() -> Dict[str, List[List[str]]]:
    global inference_patterns
    inference_file = os.path.join("inference_patterns.json")
    if os.path.exists(inference_file):
        with open(inference_file, "r", encoding="utf-8") as f:
            inference_patterns = json.load(f)
    else:
        inference_patterns = {}
    return inference_patterns

# Charge plusieurs nœuds en parallèle pour améliorer les performances
def preload_nodes_by_id_parallel(node_ids: List[int]) -> None:
    ids_to_fetch = [nid for nid in node_ids if nid not in node_cache]
    if not ids_to_fetch:
        return

    def fetch(nid):
        node = get_cached_response(f"node_by_id/{nid}")
        if node:
            node_cache[nid] = node

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        list(tqdm(executor.map(fetch, ids_to_fetch), total=len(ids_to_fetch)))





def initialize_requests():
    global relation_types, inference_patterns
    get_nodes_types()
    relation_types_list = get_relations_types() or []
    relation_types = {rel["id"]: rel for rel in relation_types_list}
    inference_patterns = load_inference_patterns()
