import discord
from discord.ext import commands, tasks
from discord import app_commands  # Importante para os Slash Commands
import random
import json
import os
from datetime import time, timezone, timedelta
from dotenv import load_dotenv

# --- CONFIGURAÇÕES ---
fuso_horario = timezone(timedelta(hours=-3))

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ID_DO_CANAL = int(os.getenv('DISCORD_CHANNEL_ID', '0')) 
CAMINHO_JSON = 'insultos.json'

if not TOKEN or ID_DO_CANAL == 0:
    print("ERRO: As variáveis DISCORD_TOKEN ou DISCORD_CHANNEL_ID não foram configuradas!")
    exit()

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents, chunk_guilds_at_startup=True)

# --- FUNÇÕES DE SUPORTE ---

def obter_insulto_local(categoria="gerais"):
    try:
        if not os.path.exists(CAMINHO_JSON):
            return "Erro: O arquivo de insultos sumiu do servidor!"

        with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        if categoria in dados and dados[categoria]:
            return random.choice(dados[categoria])
        
        if "gerais" in dados and dados["gerais"]:
            return random.choice(dados["gerais"])
            
        return "Não consegui pensar em um insulto agora, você deu sorte."
    except Exception as e:
        print(f"Erro ao ler o arquivo JSON: {e}")
        return "Tive um piripaque no meu banco de dados de insultos."

# --- TAREFA AGENDADA ---

horarios = [
    time(hour=13, minute=0, tzinfo=fuso_horario), 
    time(hour=17, minute=0, tzinfo=fuso_horario),
    time(hour=21, minute=0, tzinfo=fuso_horario),
]

@tasks.loop(time=horarios)
async def tarefa_agendada():
    canal = bot.get_channel(ID_DO_CANAL)
    if not canal:
        canal = await bot.fetch_channel(ID_DO_CANAL)

    insulto = obter_insulto_local("gerais")
    
    guild = canal.guild
    todos_membros = []
    async for membro in guild.fetch_members(limit=None):
        if not membro.bot:
            todos_membros.append(membro)

    if todos_membros:
        escolhido = random.choice(todos_membros)
        await canal.send(f"🚨 **Atenção {escolhido.mention}!**\n> {insulto}")
    else:
        await canal.send(f"🚨 **Atenção @everyone!**\n> {insulto}")

# --- EVENTOS E SINCRONIZAÇÃO ---

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} online!')
    
    # IMPORTANTE: Sincroniza os comandos globais com o Discord para eles aparecerem no chat
    try:
        sincronizados = await bot.tree.sync()
        print(f"🔄 Sincronizados {len(sincronizados)} comando(s) de barra globalmente!")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    if not tarefa_agendada.is_running():
        tarefa_agendada.start()

# --- SLASH COMMANDS (COMANDOS DE BARRA) ---

# Mudamos de @bot.command() para @bot.tree.command()
@bot.tree.command(name='insultar', description='Envia um insulto aleatório para o membro mencionado.')
@app_commands.describe(membro='O membro que você deseja insultar') # Descrição do argumento no Discord
async def enviar_direto(interaction: discord.Interaction, membro: discord.Member):
    """Envia um insulto da lista 'gerais' para o membro mencionado."""
    
    # Comandos de barra usam 'interaction' em vez de 'ctx'
    # É preciso dar um "responder" à interação
    if membro == bot.user:
        insulto = obter_insulto_local("gerais")
        await interaction.response.send_message(
            f"Achou que ia me usar contra mim mesmo, {interaction.user.mention}? Toma essa:\n> {insulto}"
        )
        return

    insulto = obter_insulto_local("gerais")
    await interaction.response.send_message(
        f"Ei {membro.mention}, o {interaction.user.display_name} mandou te dizer:\n> {insulto}"
    )

bot.run(TOKEN)