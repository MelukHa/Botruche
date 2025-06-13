# Botruche 2.0

## Projet réalisé dans le cadre du Master IASD (cours Langage Naturel 1)  
**Encadrant : Matthieu Lafourcade**

Ce projet permet de réaliser des **inférences sémantiques** entre mots à partir de l’API **JeuxDeMots**.  
Il propose une interface **via Discord** et un mode **ligne de commande** pour les tests locaux.

---

## Structure du projet

- `discordbot.py` : Interface Discord. Le bot écoute les messages et répond aux requêtes d’inférence.
- `cli.py` : Mode interactif en ligne de commande, pour tester sans Discord.
- `request_api.py` : Fonctions d’accès à l’API JDM, avec mise en cache locale.
- `inference.py` : Logique d’inférence sémantique (exploration, pondération, synthèse).
- `inference_patterns.json` : Schémas d’inférence à deux relations (personnalisables).
- `requirements.txt` : Fichier des dépendances Python.

---

## Installation

### Installer les dépendances

```
pip install -r requirements.txt
```

---

## Utilisation avec Discord

1. Créez un bot Discord sur https://discord.com/developers
2. Copiez son **token**
3. Dans `.env`, remplacez :
   <your_discord_token_here> par votre token discord

4. Invitez le bot sur votre serveur discord
5. Lancez le bot :
   ```
   python discordbot.py
   ```

Le bot répondra automatiquement aux messages textuels contenant des requêtes du type :

mot1 relation mot2

Exemple : `chat r_agent-1 miauler`

---

## Utilisation en ligne de commande (mode terminal)

Si vous ne souhaitez pas utiliser Discord :

```
python cli.py
```

Cela lance un **mode interactif** dans lequel vous pouvez taper des requêtes comme :

```
>>> chat r_agent-1 miauler
>>> tigre r_carac dangereux
```

Tapez `exit` pour quitter.

---

## Exemples de requêtes

- `cuire r_patient steak`
- `serveuse r_agent-1 apporter à boire`
- `autruche r_agent-1 voler`

La réponse inclut :
- Les relations directes (si existantes)
- Des inférences indirectes via un nœud intermédiaire
- Une conclusion finale (`✅ probable`, `❌ improbable`, `❓ incertain`) selon le score et le nombre de preuves.

---

## Dépendances (requirements.txt)

```
requests
tqdm
python-dotenv
discord (si utilisation du bot discord)
```

---

## Cache

Les fichiers de l’API sont automatiquement mis en cache dans un dossier `cache/` pour éviter de surcharger le serveur de JeuxDeMots.  
Ce cache est nettoyé automatiquement à chaque lancement du bot (fichiers de plus de 1 mois).

---

## Ouvertures possibles

Initialement je comptais utiliser l'API Groq pour pouvoir gérer le langage naturel et demander à un LLM de formatter automatiquement les demandes "Est-ce que mot1 relation mot2" en "mot1 relation mot2", et de même avec les relations trouvées (les formuler en phrases pour avoir des réponses claires), mais par manque de temps je n'ai pas pu ajouter cette fonctionnalité.

---
