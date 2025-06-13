import os
import time
import discord
from discord.ext import commands
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from inference import infer_relation
from request_api import initialize_requests

# Charger les variables du fichier .env
load_dotenv()

# Récupérer la variable TOKEN
TOKEN = os.getenv("TOKEN")
 
#ADMIN = 'Votre identifiant administrateur' # identifiant d'un utilisateur qui a les droits d'administrations sur le bot
#CHANNEL = 'Un identifiant de channel' # Précise dans quel channel le bot va traiter les messages

LAST_REQUETE = None
REQUETE = []
EN_REQUETE = False
 
intents = discord.Intents.default()
intents.message_content = True
activity = discord.Activity(type=discord.ActivityType.listening, name="OIIAOIIA EXTENDED")
 
#client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='/', activity=activity, intents=intents, help_command=None)

# File d'attente pour gérer les messages en attente
message_queue = asyncio.Queue()
processing_request = False  # Indique si une requête est en cours



async def process_request():
    global processing_request

    loop = asyncio.get_running_loop()

    while True:
        message = await message_queue.get()
        processing_request = True  # Indique qu'un traitement est en cours

        message_text = message.content.split()
        print(message_text)

        start = time.time()

        # Lancement de l'inférence dans un thread séparé
        result = await loop.run_in_executor(None, infer_relation, message_text[0], message_text[1], message_text[2])

        print(f"Temps écoulé : {time.time() - start:.2f}s")
        #print(result)

        await message.reply("\n".join(result))  # Transforme liste en chaîne de lignes

        message_queue.task_done()
        processing_request = False  # Libérer pour la prochaine requête



@bot.event #startup, on supprime les caches trop vieux ou corrompus
async def on_ready():
    #await bot.change_presence(activity=discord.Game(name="Minecraft Forge (RLCraft)"))
    dossier_cache = 'cache/'
    nb_sec_semaine = 7 * 24 * 60 * 60 * 4 # 1 mois en secondes
    removed = 0

    # Parcourir tous les fichiers du dossier cache
    for nom_fichier in os.listdir(dossier_cache):
        chemin_fichier = os.path.join(dossier_cache, nom_fichier)

        # Vérifier si le fichier a plus d'une semaine ou s'il est mal formaté
        try:
            with open(chemin_fichier, 'r') as f:
                contenu = f.read()
        except Exception:
            erreurs_ouvertures += 1
            os.remove(chemin_fichier)
            removed += 1
            continue

        if (
            (time.time() - os.path.getmtime(chemin_fichier)) > nb_sec_semaine
            or contenu.startswith("MUTED")
        ):
            os.remove(chemin_fichier)
            removed += 1

    print(f"[CACHE] {removed} fichiers supprimés (trop vieux ou invalides)")

    initialize_requests()
    print(f'{bot.user} has connected to Discord !')

   # Crée un pool de threads pour exécuter les fonctions bloquantes
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    bot.loop.set_default_executor(executor)

    # Lancer la boucle de traitement des messages
    bot.loop.create_task(process_request())


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignorer les messages du bot lui-même
    
    print(f'Message from {message.author} : {message.content}')
    #print(message)
    await message.channel.typing()
    await message_queue.put(message)  # Ajouter à la file d'attente

    return

bot.run(TOKEN)
#client.run(TOKEN)
