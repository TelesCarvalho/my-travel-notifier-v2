import os
import time
import traceback
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

def enviar_foto_telegram(caminho_foto, legenda):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and os.path.exists(caminho_foto):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        try:
            with open(caminho_foto, "rb") as foto:
                requests.post(
                    url,
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": legenda, "parse_mode": "Markdown"},
                    files={"photo": foto},
                    timeout=15
                )
        except Exception as e:
            print(f"Erro ao enviar foto no Telegram: {e}")

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
    
    campo_datas = driver.find_element(By.NAME, "datas")
    campo_datas.clear()
    campo_datas.send_keys("31/12/2026 - 03/01/2027")
    
    driver.find_element(By.NAME, "adultos").send_keys("2")
    driver.find_element(By.ID, "regime-pensao").send_keys("Pensão Completa")
    
    btn_buscar = driver.find_element(By.ID, "search-submit")
    driver.execute_script("arguments[0].click();", btn_buscar)
    
    # Aguarda até 20s o site responder com o botão de reservar OU a mensagem de indisponível
    WebDriverWait(driver, 20).until(
        lambda d: "não existe disponibilidade" in d.find_element(By.TAG_NAME, "body").text.lower()
        or len(d.find_elements(By.XPATH, "//a[contains(@class, 'set-disponibilidade-session')]")) > 0
    )
    
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    
    if "não existe disponibilidade" in body_text:
        print("Nenhuma vaga encontrada nesta verificação.")
    else:
        print("🚨 VAGA DETECTADA! Disparando notificação e iniciando auto-booking...")
        enviar_telegram("🚨 *VAGA ENCONTRADA NO SESC!*\n📅 Período: 31/12/2026 a 03/01/2027\n🤖 *Iniciando tentativa de reserva automática no seu CPF...*")
        
        etapa = "Iniciando checkout"
        try:
            etapa = "1. Clicar no botão Reservar"
            btn_reservar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'set-disponibilidade-session')]")))
            driver.execute_script("arguments[0].click();", btn_reservar)
            
            etapa = "2. Preencher CPF e Senha"
            campo_cpf = wait.until(EC.presence_of_element_located((By.ID, "login-form-username")))
            campo_cpf.send_keys(SESC_CPF)
            
            campo_senha = driver.find_element(By.ID, "login-form-password")
            campo_senha.send_keys(SESC_SENHA)
            
            etapa = "3. Clicar em Entrar no login"
            btn_entrar = driver.find_element(By.ID, "login-form-submit")
            driver.execute_script("arguments[0].click();", btn_entrar)
            
            etapa = "4. Clicar em Avançar para Pagamento (btn-efetuar-pgto)"
            btn_efetuar_pgto = wait.until(EC.element_to_be_clickable((By.ID, "btn-efetuar-pgto")))
            driver.execute_script("arguments[0].click();", btn_efetuar_pgto)
            
            etapa = "5. Marcar aceite do termo (contrato-aceite-covid)"
            chk_covid = wait.until(EC.presence_of_element_located((By.ID, "contrato-aceite-covid")))
            if not chk_covid.is_selected():
                driver.execute_script("arguments[0].click();", chk_covid)
                
            etapa = "6. Confirmar termo (chk-aceitar-termo)"
            btn_aceitar = wait.until(EC.element_to_be_clickable((By.ID, "chk-aceitar-termo")))
            driver.execute_script("arguments[0].click();", btn_aceitar)
            
            time.sleep(5) # Garante a retenção no carrinho
            
            print("✅ Reserva retida no carrinho com sucesso!")
            enviar_telegram("🛒 *RESERVA GARANTIDA NO SEU CARRINHO!*\n⏰ A vaga está presa no seu CPF. Acesse o site do Sesc agora para efetuar o pagamento e incluir sua acompanhante!\n\n🤖 *O robô foi DESATIVADO automaticamente para evitar novas reservas.*")
            
            desativar_workflow_github()

        except Exception as err_booking:
            tipo_erro = type(err_booking).__name__
            url_atual = driver.current_url
            print(f"Falha na etapa [{etapa}] ({tipo_erro}): {err_booking}")
            traceback.print_exc()
            
            driver.save_screenshot("erro_reserva.png")
            legenda_erro = (
                f"⚠️ *VAGA ENCONTRADA, mas falhou na etapa:*\n`{etapa}`\n"
                f"🔍 *Erro:* `{tipo_erro}`\n"
                f"🌐 *URL:* {url_atual}\n\n"
                f"🏃‍♂️ *Entre no site AGORA e tente reservar manualmente!*"
            )
            enviar_foto_telegram("erro_reserva.png", legenda_erro)

finally:
    driver.quit()
