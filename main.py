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
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

def enviar_telegram(mensagem):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=10)
        except Exception as e:
            print(f"Erro ao enviar mensagem no Telegram: {e}")

def desativar_workflow_github():
    """Trava o robô no GitHub Actions impedindo execuções futuras após o sucesso."""
    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/workflows/autobooking.yml/disable"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.put(url, headers=headers)
        if res.status_code == 204:
            print("🔒 Workflow desativado com sucesso! O robô não efetuará novas reservas.")
        else:
            print(f"Erro ao tentar desativar workflow: {res.status_code} - {res.text}")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    print("Acessando o Portal do Sesc...")
    driver.get("https://portalturismo.sescgo.com.br/")

    # 1. Preenchimento dos Parâmetros de Busca (31/12/2026 a 03/01/2027)
    wait.until(EC.presence_of_element_located((By.ID, "search-unidade")))
    driver.find_element(By.ID, "search-unidade").send_keys("Caldas Novas")
    
    # Campo de crianças mantido intacto em "Selecionar"
    
    campo_datas = driver.find_element(By.NAME, "datas")
    campo_datas.clear()
    campo_datas.send_keys("31/12/2026 - 03/01/2027")
    
    campo_adultos = driver.find_element(By.NAME, "adultos")
    campo_adultos.clear()
    campo_adultos.send_keys("2")
    
    driver.find_element(By.ID, "regime-pensao").send_keys("Pensão Completa")
    
    btn_buscar = driver.find_element(By.ID, "search-submit")
    driver.execute_script("arguments[0].click();", btn_buscar)
    
    time.sleep(5)
    
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    
    if "não existe disponibilidade" in body_text:
        print("Nenhuma vaga encontrada nesta verificação.")
    else:
        print("🚨 VAGA DETECTADA! Disparando notificação e iniciando auto-booking...")
        enviar_telegram("🚨 *VAGA ENCONTRADA NO SESC!*\n📅 Período: 31/12/2026 a 03/01/2027\n🤖 *Iniciando tentativa de reserva automática no seu CPF...*")
        
        try:
            # 2. Clicar no Botão Reservar
            btn_reservar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'set-disponibilidade-session')]")))
            driver.execute_script("arguments[0].click();", btn_reservar)
            
            # 3. Autenticação na Conta
            campo_cpf = wait.until(EC.presence_of_element_located((By.ID, "login-form-username")))
            campo_cpf.send_keys(SESC_CPF)
            
            campo_senha = driver.find_element(By.ID, "login-form-password")
            campo_senha.send_keys(SESC_SENHA)
            
            btn_entrar = driver.find_element(By.ID, "login-form-submit")
            driver.execute_script("arguments[0].click();", btn_entrar)
            
            # 4. Tela de Integrantes (Titular) -> Avançar para Pagamento
            btn_efetuar_pgto = wait.until(EC.element_to_be_clickable((By.ID, "btn-efetuar-pgto")))
            driver.execute_script("arguments[0].click();", btn_efetuar_pgto)
            
            # 5. Aceite do Termo
            chk_covid = wait.until(EC.presence_of_element_located((By.ID, "contrato-aceite-covid")))
            if not chk_covid.is_selected():
                driver.execute_script("arguments[0].click();", chk_covid)
                
            btn_aceitar = wait.until(EC.element_to_be_clickable((By.ID, "chk-aceitar-termo")))
            driver.execute_script("arguments[0].click();", btn_aceitar)
            
            time.sleep(5) # Garante a retenção no carrinho
            
            print("✅ Reserva retida no carrinho com sucesso!")
            enviar_telegram("🛒 *RESERVA GARANTIDA NO SEU CARRINHO!*\n⏰ A vaga está presa no seu CPF. Acesse o site do Sesc agora para efetuar o pagamento e incluir sua acompanhante!\n\n🤖 *O robô foi DESATIVADO automaticamente para evitar novas reservas.*")
            
            # Trava automática do robô
            desativar_workflow_github()

        except Exception as err_booking:
            print(f"Falha durante a reserva automática: {err_booking}")
            enviar_telegram("⚠️ *VAGA ENCONTRADA, mas o robô não conseguiu concluir a reserva automática.*\n🏃‍♂️ *Entre no site AGORA e tente reservar manualmente!\n\n🔄 O robô continuará ativo monitorando as próximas rodadas.*")

finally:
    driver.quit()
