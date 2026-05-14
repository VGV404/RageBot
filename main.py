import discord
from discord.ext import commands, tasks
import requests
import random
import asyncio
from datetime import time
from deep_translator import GoogleTranslator

import os
from dotenv import load_dotenv

# --- CONFIGURAÇÕES ---
# Carrega o arquivo .env apenas se ele existir (útil para testes locais)
load_dotenv()

# Busca as informações das variáveis de ambiente
# O primeiro argumento é o nome da variável na Railway
# O segundo é um valor padrão caso não encontre (opcional)
TOKEN = os.getenv('DISCORD_TOKEN')
ID_DO_CANAL = int(os.getenv('DISCORD_CHANNEL_ID', '0')) 
URL_API = "https://evilinsult.com/generate_insult.php?lang=en&type=json"

# Verificação de segurança para garantir que as variáveis foram carregadas
if not TOKEN or ID_DO_CANAL == 0:
    print("ERRO: As variáveis DISCORD_TOKEN ou DISCORD_CHANNEL_ID não foram configuradas!")
    exit()


intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- FUNÇÕES DE SUPORTE ---

def buscar_e_traduzir():
    """Função síncrona para buscar o insulto e traduzir."""
    try:
        response = requests.get(URL_API, timeout=10)
        original = response.json().get('insult', 'Error')
        
        # Traduzindo do inglês para o português
        traducao = GoogleTranslator(source='en', target='pt').translate(original)
        return traducao
    except Exception as e:
        print(f"Erro na integração: {e}")
        return "Não consegui pensar em um insulto agora, você deu sorte."

async def obter_insulto_async():
    """Roda a função síncrona em uma thread separada para não travar o bot."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, buscar_e_traduzir)

# --- TAREFA AGENDADA (2x AO DIA) ---

# Defina os horários (ex: 10:00 e 22:00)
horarios = [time(hour=13, minute=0), time(hour=16, minute=59)]

@tasks.loop(time=horarios)
async def tarefa_agendada():
    canal = bot.get_channel(ID_DO_CANAL)
    if not canal:
        return

    # Filtra membros que não são bots
    membros = [m for m in canal.guild.members if not m.bot]
    
    if membros:
        escolhido = random.choice(membros)
        insulto_pt = await obter_insulto_async()
        
        await canal.send(f"🚨 **Atenção {escolhido.mention}!**\n> {insulto_pt}")

# --- COMANDOS E EVENTOS ---

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} online e operando em {len(bot.guilds)} servidor(es)!')
    if not tarefa_agendada.is_running():
        tarefa_agendada.start()

@bot.command(name='enviar')
@commands.cooldown(1, 90, commands.BucketType.user) # 1 uso a cada 90s por pessoa
async def enviar_direto(ctx, membro: discord.Member):
    """Envia um insulto traduzido para o membro mencionado."""
    async with ctx.typing(): # Mostra "Digitando..." enquanto traduz
        insulto_pt = await obter_insulto_async()
        await ctx.send(f"Ei {membro.mention}, o {ctx.author.display_name} mandou te dizer:\n> {insulto_pt}")

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