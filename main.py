import discord
from discord.ext import commands, tasks
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

# Verificação de segurança
if not TOKEN or ID_DO_CANAL == 0:
    print("ERRO: As variáveis DISCORD_TOKEN ou DISCORD_CHANNEL_ID não foram configuradas!")
    exit()

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, chunk_guilds_at_startup=True)

# --- FUNÇÕES DE SUPORTE ---

def obter_insulto_local(categoria="gerais"):
    """Lê o arquivo JSON local e retorna um insulto aleatório da categoria especificada."""
    try:
        if not os.path.exists(CAMINHO_JSON):
            return "Erro: O arquivo de insultos sumiu do servidor!"

        with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Garante que a categoria existe e não está vazia
        if categoria in dados and dados[categoria]:
            return random.choice(dados[categoria])
        
        # Fallback caso a categoria específica falhe mas a 'gerais' exista
        if "gerais" in dados and dados["gerais"]:
            return random.choice(dados["gerais"])
            
        return "Não consegui pensar em um insulto agora, você deu sorte."
    except Exception as e:
        print(f"Erro ao ler o arquivo JSON: {e}")
        return "Tive um piripaque no meu banco de dados de insultos."

# --- TAREFA AGENDADA (3x AO DIA) ---

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

    # Usa a lista "gerais" para o envio automático por padrão
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

# --- COMANDOS E EVENTOS ---

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} online e operando em {len(bot.guilds)} servidor(es)!')
    if not tarefa_agendada.is_running():
        tarefa_agendada.start()

@bot.command(name='enviar')
@commands.cooldown(1, 90, commands.BucketType.user) # 1 uso a cada 90s por pessoa
async def enviar_direto(ctx, membro: discord.Member):
    """Envia um insulto da lista 'gerais' para o membro mencionado."""
    if membro == bot.user:
        insulto = obter_insulto_local("gerais")
        await ctx.send(f"Achou que ia me usar contra mim mesmo, {ctx.author.mention}? Toma essa:\n> {insulto}")
        return

    insulto = obter_insulto_local("gerais")
    await ctx.send(f"Ei {membro.mention}, o {ctx.author.display_name} mandou te dizer:\n> {insulto}")

# --- TRATAMENTO DE ERROS ---

@enviar_direto.error
async def enviar_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Calma! Você só pode insultar alguém novamente em {error.retry_after:.1f}s.", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Não encontrei esse usuário. Marque alguém corretamente (ex: !enviar @usuario).")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❓ Você precisa mencionar alguém. Exemplo: `!enviar @Nome`.")

bot.run(TOKEN)