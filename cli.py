from request_api import *
from inference import infer_relation

# --- Mode interactif console (facultatif, pour tests sans Discord) ---

if __name__ == "__main__":
    print("=== Mode interactif JDM ===")
    print("Tapez une requête du type : mot1 relation mot2")
    print("Tapez 'exit' pour quitter.\n")

    initialize_requests()

    while True:
        ligne = input(">>> ")
        if ligne.strip().lower() in {"exit", "quit"}:
            break
        if not ligne.strip():
            continue
        try:
            mot1, relation, mot2 = ligne.strip().split(maxsplit=2)
            résultats = infer_relation(mot1, relation, mot2)
            print("\n".join(résultats))
        except ValueError:
            print("❌ Format invalide. Attendu : <mot1> <relation> <mot2>\n")
        except Exception as e:
            print(f"❌ Erreur pendant l’inférence : {e}\n")
