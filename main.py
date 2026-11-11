import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SESC_CPF = os.environ.get("SESC_CPF")
SESC_SENHA = os.environ.get("SESC_SENHA")

def enviar_telegram(mensagem):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=10)
        except Exception as e:
            print(f"Erro ao enviar mensagem no Telegram: {e}")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    print("Acessando o Portal do Sesc (TESTE DE LOGIN)...")
    driver.get("https://portalturismo.sescgo.com.br/")

    # 1. Busca na data de teste (23/12/2026 a 24/12/2026)
    wait.until(EC.presence_of_element_located((By.ID, "search-unidade")))
    driver.find_element(By.ID, "search-unidade").send_keys("Caldas Novas")
    driver.find_element(By.ID, "search-criancas").send_keys("1")
    
    campo_datas = driver.find_element(By.NAME, "datas")
    campo_datas.clear()
    campo_datas.send_keys("23/12/2026 - 24/12/2026")
    
    driver.find_element(By.NAME, "adultos").send_keys("2")
    driver.find_element(By.ID, "regime-pensao").send_keys("Pensão Completa")
    
    btn_buscar = driver.find_element(By.ID, "search-submit")
    driver.execute_script("arguments[0].click();", btn_buscar)
    
    time.sleep(5)
    
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    
    if "não existe disponibilidade" in body_text:
        print("Nenhuma vaga encontrada nas datas de teste.")
        enviar_telegram("⚠️ *TESTE:* Nenhuma vaga disponível no período de 23/12 a 24/12.")
    else:
        print("🚨 Vaga encontrada! Iniciando login e retenção da vaga...")
        enviar_telegram("🧪 *TESTE DE PRÉ-RESERVA EM ANDAMENTO!*\n📅 Período: 23/12/2026 a 24/12/2026\n🔑 Realizando login para vincular a vaga ao seu CPF...")
        
        try:
            # 2. Clicar em Reservar
            btn_reservar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'set-disponibilidade-session')]")))
            driver.execute_script("arguments[0].click();", btn_reservar)
            
            # 3. Autenticação na Conta
            campo_cpf = wait.until(EC.presence_of_element_located((By.ID, "login-form-username")))
            campo_cpf.send_keys(SESC_CPF)
            
            campo_senha = driver.find_element(By.ID, "login-form-password")
            campo_senha.send_keys(SESC_SENHA)
            
            btn_entrar = driver.find_element(By.ID, "login-form-submit")
            driver.execute_script("arguments[0].click();", btn_entrar)
            
            time.sleep(5)
            
            print("✅ Login realizado e vaga vinculada à sessão!")
            enviar_telegram("✅ *TESTE DE LOGIN CONCLUÍDO COM SUCESSO!*\n\n🛒 A vaga de teste (23/12 a 24/12) foi vinculada à sua conta no Sesc.\n📲 Acesse o portal e verifique a tela de integrantes ou *MINHAS RESERVAS*.")
            
        except Exception as err_booking:
            print(f"Falha no teste de login: {err_booking}")
            enviar_telegram(f"⚠️ *FALHA NO TESTE DE LOGIN:* {err_booking}")

finally:
    driver.quit()
