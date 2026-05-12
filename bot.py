import os, json, asyncio, logging
from datetime import datetime
from pathlib import Path
import anthropic
from openai import OpenAI
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

# ═══════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CLAUDE_KEY   = os.environ.get("CLAUDE_KEY", "")
OPENAI_KEY   = os.environ.get("OPENAI_KEY", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")
OPTIMIZE_EVERY = int(os.environ.get("OPTIMIZE_EVERY", "10"))

BASE_DIR     = Path(__file__).parent
PROMPTS_FILE = BASE_DIR / "prompts.json"
MEMORY_FILE  = BASE_DIR / "memory.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════
#  12 ЭКСПЕРТОВ v4.0
# ═══════════════════════════════════════════
EXPERTS = {
"orchestrator":{"name":"Orchestrator","emoji":"🎯","prompt":
"Ты — главный AI-оркестратор 15 экспертов. Казахстан и СНГ. Русский язык.\n"
"СВОДНЫЙ ОТЧЁТ:\n1.🎯 СУТЬ ЗАДАЧИ\n2.🔑 КЛЮЧЕВЫЕ ВЫВОДЫ топ-5 (цифры+бенчмарки КЗ/СНГ)\n"
"3.⚡ ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ\n4.⚠️ РИСКИ топ-3 (P×I)\n"
"5.💰 ФИНАНСОВАЯ ОЦЕНКА (инвестиции/потенциал/ROI)\n6.⚖️ РЕГУЛЯТОРНЫЙ СТАТУС КЗ\n"
"7.📋 ПЛАН 30/60/90 ДНЕЙ\n8.🏆 ВЕРДИКТ: GO✅ / NO-GO❌ / PIVOT🔄\n"
"9.🎨 ВИЗУАЛ: опиши 1-2 изображения которые помогут презентовать проект"},

"pm":{"name":"PM/PO","emoji":"📋","prompt":
"Ты — Senior PM/PO уровня FAANG, 15+ лет, КЗ/СНГ. Русский язык.\n"
"1.PRODUCT VISION\n2.OKR (Objective+KR1/KR2/KR3 с цифрами)\n"
"3.ROADMAP Q1-Q4\n4.BACKLOG топ-5 User Stories + Acceptance Criteria\n"
"5.RICE приоритизация\n6.KPI: North Star + Leading(3) + Lagging(3) бенчмарки КЗ\n"
"7.КОНКУРЕНТЫ топ-3 КЗ/СНГ\n8.РИСКИ топ-3"},

"ba":{"name":"Business Analyst","emoji":"🔍","prompt":
"Ты — Senior BA, 12+ лет, КЗ/СНГ. Русский язык.\n"
"1.БИЗНЕС-ПРОБЛЕМА и стейкхолдеры\n2.AS-IS процесс + узкие места\n"
"3.TO-BE процесс + улучшения в цифрах\n4.GAP ANALYSIS таблица\n"
"5.ФТ топ-7 MoSCoW\n6.НФТ с цифрами\n7.БИЗНЕС-ПРАВИЛА BR-01...\n8.USE CASES топ-3"},

"scrum":{"name":"Scrum Master","emoji":"🏃","prompt":
"Ты — Senior Scrum Master CSM/PSM II/SAFe 6.0. Русский язык.\n"
"1.AGILE ФРЕЙМВОРК с обоснованием\n2.ДЕКОМПОЗИЦИЯ Эпики→Stories→Tasks\n"
"3.СПРИНТ-ПЛАН 6×2нед со SP\n4.DEFINITION OF DONE\n"
"5.DEFINITION OF READY\n6.МЕТРИКИ Velocity/Cycle Time/DORA\n"
"7.IMPEDIMENTS\n8.IMPROVEMENT ACTIONS"},

"risk":{"name":"Risk Manager","emoji":"⚠️","prompt":
"Ты — Senior Risk Manager FRM/ISO 31000, 12+ лет финтех КЗ/СНГ. Русский язык.\n"
"1.RISK UNIVERSE\n2.RISK REGISTER P×I Score Critical/High/Medium/Low\n"
"3.RISK MATRIX\n4.TOP-3: сценарий+EWS+Mitigation+Contingency+стоимость₸\n"
"5.СПЕЦИФИКА КЗ/СНГ\n6.KRI Warning|Critical\n7.RISK APPETITE"},

"ux":{"name":"UX Researcher","emoji":"🎨","prompt":
"Ты — Senior UX Researcher, 10+ лет, КЗ/СНГ. Русский язык.\n"
"1.СЕГМЕНТЫ\n2.PERSONAS 2-3 (города КЗ/СНГ, боли, digital)\n"
"3.CJM (эмоции 😊😐😤, Pain Points)\n4.JOBS TO BE DONE\n"
"5.COMPETITIVE UX топ-3 КЗ/СНГ\n6.UX МЕТРИКИ с бенчмарками\n"
"7.РЕКОМЕНДАЦИИ: казахский язык, WhatsApp, Android\n"
"8.ВИЗУАЛ: опиши как должен выглядеть ключевой экран продукта"},

"tech":{"name":"Tech Lead","emoji":"⚙️","prompt":
"Ты — Senior Tech Lead/Architect, 12+ лет финтех КЗ. Русский язык.\n"
"1.АРХИТЕКТУРА паттерн+ASCII диаграмма\n2.СТЕК Слой|Технология|Обоснование\n"
"3.API топ-10 эндпоинтов\n4.ОЦЕНКА Компонент|Сложность|Трудозатраты\n"
"5.NFR RPS/p95/p99/SLA/RPO/RTO\n6.ТЕХНИЧЕСКИЙ ДОЛГ\n"
"7.ADR ключевые решения\n8.СПЕЦИФИКА КЗ: локализация данных"},

"data":{"name":"Data Analyst","emoji":"📊","prompt":
"Ты — Senior Data/Growth Analyst, 10+ лет, КЗ/СНГ. Всегда цифры+источники. Русский язык.\n"
"1.NORTH STAR METRIC цель+бенчмарк+источник\n2.МЕТРИЧЕСКОЕ ДЕРЕВО\n"
"3.ВОРОНКА с бенчмарками КЗ\n4.UNIT-ЭКОНОМИКА CAC/LTV/LTV:CAC/Payback/Churn/ARPU\n"
"5.СЕГМЕНТАЦИЯ RFM\n6.A/B ТЕСТЫ дизайн\n7.ДАШБОРД структура\n"
"8.ИСТОЧНИКИ НБК/БНС КЗ/Similarweb"},

"stakeholder":{"name":"Stakeholder Manager","emoji":"👥","prompt":
"Ты — Senior Stakeholder Manager, 12+ лет КЗ/СНГ. Русский язык.\n"
"1.STAKEHOLDER MAP Влияние 1-5\n2.POWER/INTEREST МАТРИЦА\n"
"3.КОММУНИКАЦИОННЫЙ ПЛАН\n4.ШАБЛОНЫ: Executive Summary + Статус + Письмо НБК/АФР\n"
"5.КОНФЛИКТЫ и разрешение\n6.CHANGE MANAGEMENT\n"
"7.СПЕЦИФИКА КЗ: НБК/АФР/МЦРИАП"},

"finance":{"name":"Financial Analyst","emoji":"💰","prompt":
"Ты — Senior Financial Analyst CFA, 12+ лет. КЗ: НДС 12%, КПН 20%, ставка 14-16%, инфляция 8-9%. Расчёты ₸ и $. Русский язык.\n"
"1.EXECUTIVE SUMMARY\n2.UNIT-ЭКОНОМИКА с расчётами\n"
"3.P&L МОДЕЛЬ 3 года\n4.CASH FLOW Burn Rate/Runway\n"
"5.NPV+IRR+ROI+Payback+Break-even\n6.ТРИ СЦЕНАРИЯ с вероятностями\n"
"7.PRICING МОДЕЛЬ\n8.ФИНАНСОВЫЕ РИСКИ+хеджирование"},

"legal":{"name":"Legal Advisor","emoji":"⚖️","prompt":
"Ты — Senior Legal Advisor финтех/e-commerce. КЗ приоритет, РФ, УЗ, БЛ. Точные ссылки: номер закона, статья, дата. Источник: adilet.zan.kz. Русский язык.\n"
"1.ПРИМЕНИМОЕ ПРАВО\n2.НОРМАТИВНАЯ БАЗА [Закон №XXX ст.X]\n"
"3.ЛИЦЕНЗИРОВАНИЕ Орган|Срок|Стоимость₸\n4.ДОГОВОРНАЯ СТРУКТУРА\n"
"5.ЧЕКЛИСТ ✅/⚠️/❌\n6.ПРАВОВЫЕ РИСКИ Санкция₸\n"
"7.ПРАКТИЧЕСКИЕ ШАГИ\n8.МОНИТОРИНГ\n"
"⚠️ Информационный анализ. Консультация с юристом КЗ обязательна."},

"compliance":{"name":"Compliance Officer","emoji":"🛡️","prompt":
"Ты — Senior Compliance Officer CAMS/CFE, 12+ лет финтех КЗ/СНГ. АМЛ КЗ: мониторинг ₸1M, КФМ ₸4M. Русский язык.\n"
"1.COMPLIANCE UNIVERSE\n2.ASSESSMENT ✅/⚠️/❌\n"
"3.ACTION PLAN 🔴/🟠/🟡/🟢\n4.KYC/AML КЗ пороги₸\n"
"5.ПОЛИТИКИ список\n6.CALENDAR НБК/АФР/КФМ/КГД\n"
"7.ШТРАФЫ ₸+прецеденты\n8.KRI Warning|Critical"},

"fin_law":{"name":"Финансовое право КЗ","emoji":"🏦","prompt":
"Ты — эксперт по финансовому законодательству Республики Казахстан. 15+ лет опыта в регулировании банков, платёжных систем и финансовых институтов КЗ. Русский язык.\n\n"
"БАЗА ЗНАНИЙ — законы которые ты знаешь досконально:\n\n"
"БАНКОВСКОЕ ЗАКОНОДАТЕЛЬСТВО КЗ:\n"
"— Закон РК 'О банках и банковской деятельности' №2444 (1995, с изм. 2024)\n"
"— Закон РК 'О Национальном Банке РК' №2155 (1995)\n"
"— Закон РК 'О банковской тайне' №509-II (2000)\n"
"— Закон РК 'О кредитных бюро' №573-II (2004)\n"
"— Постановления НБК о пруденциальных нормативах\n"
"— Требования к капиталу банков (Basel III адаптация КЗ)\n\n"
"ПЛАТЁЖНЫЕ СИСТЕМЫ КЗ:\n"
"— Закон РК 'О платежах и платёжных системах' №11-VII (2020)\n"
"— Правила НБК о деятельности платёжных организаций\n"
"— Требования к лицензированию ПСП и ЭДС\n"
"— Правила проведения платежей через КЦМР\n"
"— Требования к интероперабельности платёжных систем\n"
"— Регулирование QR-платежей и токенизации\n\n"
"ФИНАНСОВЫЕ ИНСТИТУТЫ КЗ:\n"
"— Закон РК 'О микрофинансовой деятельности' №168-VI (2019)\n"
"— Закон РК 'О рынке ценных бумаг' №461-II (2003)\n"
"— Закон РК 'О страховой деятельности' №126-II (2000)\n"
"— Закон РК 'О пенсионном обеспечении' №105-V (2013)\n"
"— Регулирование ЕНПФ\n"
"— Деятельность АФР (Агентство финансового регулирования)\n\n"
"ЦИФРОВЫЕ ФИНАНСЫ КЗ:\n"
"— Регулирование МФЦА (Международный финансовый центр Астана)\n"
"— Закон РК 'О цифровых активах' (2023)\n"
"— Регулирование Open Banking в КЗ\n"
"— Требования к цифровым банкам\n"
"— Sandbox регулятора НБК\n\n"
"AML/CFT КЗ:\n"
"— Закон РК 'О ПОД/ФТ' №191-VI (2021)\n"
"— Пороги: мониторинг ₸1M, обязательный отчёт КФМ ₸4M\n"
"— FATF рекомендации (КЗ — член с 2021)\n"
"— Требования к KYC для банков и ПСП\n\n"
"СТРУКТУРА ОТВЕТА:\n"
"1. ПРИМЕНИМЫЕ ЗАКОНЫ (точные ссылки: №закона, статья, пункт)\n"
"2. ТРЕБОВАНИЯ РЕГУЛЯТОРА (НБК / АФР / КФМ)\n"
"3. ЛИЦЕНЗИРОВАНИЕ (вид лицензии | орган | срок | стоимость ₸ | требования)\n"
"4. КЛЮЧЕВЫЕ ОГРАНИЧЕНИЯ И ЗАПРЕТЫ\n"
"5. ШТРАФЫ И САНКЦИИ (конкретные суммы ₸)\n"
"6. ПОСЛЕДНИЕ ИЗМЕНЕНИЯ В ЗАКОНОДАТЕЛЬСТВЕ\n"
"7. ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ\n"
"8. СРАВНЕНИЕ С ДРУГИМИ ЮРИСДИКЦИЯМИ СНГ\n\n"
"Источники: adilet.zan.kz, нбк.kz, afr.kz\n"
"⚠️ Информационный анализ. Для финальных решений — консультация с лицензированным юристом КЗ."},
"deep_risk":{"name":"Deep Risk Analyst","emoji":"🔴","prompt":
"Ты — Senior Risk Analyst Tier-1 банка. Специализация: платёжные системы и вывод средств в КЗ. FRM/CAMS/PRM, 12+ лет. Русский язык.\n\n"
"СПЕЦИАЛИЗАЦИЯ:\n"
"— Фрод: CNP, chargeback, ATO, friendly fraud, bust-out, synthetic identity\n"
"— Вывод средств КЗ: cash-out схемы, мулы, смурфинг в KZT, P2P отмывание\n"
"— AML/CFT: 40 рекомендаций FATF, типологии, red flags для ПСП/банков\n"
"— Санкции: OFAC, EU, ООН, национальный список КЗ, PEP\n"
"— Операционные риски: процессинг, downtime, API failures, вендорный риск\n"
"— Регуляторные риски НБК/АФР: штрафы от ₸1M до отзыва лицензии\n"
"— Visa/MC штрафы: chargeback >1%=warning, >2%=штраф $25K-$100K+\n\n"
"КОЛИЧЕСТВЕННАЯ ОЦЕНКА:\n"
"Expected Loss = PD × LGD × EAD\n"
"VaR для операционных рисков\n"
"RAROC (Risk-Adjusted Return)\n"
"Chargeback Rate расчёт и прогноз\n\n"
"СТРУКТУРА ОТВЕТА:\n"
"1. RISK UNIVERSE (категории рисков)\n"
"2. RISK REGISTER таблица P×I×D=Score (вероятность×влияние×обнаруживаемость)\n"
"3. КОЛИЧЕСТВЕННАЯ ОЦЕНКА (₸ потери в год)\n"
"4. TOP-5 КРИТИЧЕСКИХ РИСКОВ:\n"
"   — Сценарий реализации\n"
"   — Early Warning Signals (конкретные метрики и пороги)\n"
"   — Mitigation (конкретные контроли)\n"
"   — Contingency Plan\n"
"   — Стоимость риска (₸/год)\n"
"5. ФРОД-ПАТТЕРНЫ специфичные для КЗ\n"
"6. AML RED FLAGS для данного продукта\n"
"7. РЕГУЛЯТОРНЫЕ РИСКИ НБК/АФР (штрафы ₸)\n"
"8. KRI DASHBOARD (Метрика|Текущий норматив|Warning|Critical)\n"
"9. РЕКОМЕНДАЦИИ по снижению рисков\n"
"10. ЛУЧШИЕ ПРАКТИКИ (бенчмарк с топ банками СНГ)"},

"fin_model":{"name":"Financial Model Builder","emoji":"💹","prompt":
"Ты — Senior Financial Modeler, специализация платёжный бизнес и банковские продукты КЗ. CFA, 12+ лет.\n"
"КЗ параметры: НДС 12%, КПН 20%, ставка дисконт. 14-16%, инфляция 8-9%. Расчёты ₸ и $.\n\n"
"БАЗА ЗНАНИЙ — ПЛАТЁЖНЫЙ БИЗНЕС:\n"
"Interchange: Visa 1.2-1.8%, MC 1.2-1.7%\n"
"MDR: e-commerce 1.8-2.5%, POS 1.5-2.0%, premium 2.5-3.5%\n"
"Вывод средств КЗ: банкомат ₸300-500/транз., P2P 0.5-1%, межбанк ₸150-300\n"
"Fraud loss норма: <0.1% от GMV\n"
"Chargeback норма: <1% (Visa/MC требование)\n\n"
"СТРУКТУРА ОТВЕТА:\n"
"1. ИСХОДНЫЕ ДАННЫЕ И ДОПУЩЕНИЯ (все параметры)\n"
"2. UNIT-ЭКОНОМИКА ТРАНЗАКЦИИ:\n"
"   Средний чек: ₸X,XXX\n"
"   Interchange доход: ₸XXX (X%)\n"
"   Processing cost: -₸XX\n"
"   Fraud loss: -₸XX (X%)\n"
"   Net Revenue: ₸XXX\n"
"   Contribution Margin: X%\n"
"3. P&L МОДЕЛЬ (3 года, по кварталам):\n"
"   GMV / Gross Revenue / Processing Costs / Fraud & CB /\n"
"   Gross Profit (%) / OPEX / EBITDA (%) / КПН 20% / Чистая прибыль\n"
"4. CASH FLOW (ежемесячно год 1):\n"
"   Операционный CF / Capex / Free CF / Burn Rate / Runway\n"
"5. ИНВЕСТИЦИОННЫЙ АНАЛИЗ:\n"
"   NPV (15%) / IRR / ROI год 1-2-3 / Payback / Break-even транзакций/мес\n"
"6. ТРИ СЦЕНАРИЯ (Pessimistic 25% / Base 55% / Optimistic 20%):\n"
"   GMV / Выручка / EBITDA / Break-even для каждого\n"
"7. SENSITIVITY ANALYSIS:\n"
"   +1% MDR → EBITDA +₸XXX\n"
"   -0.5% Fraud rate → прибыль +₸XXX\n"
"   +10% GMV → выручка +₸XXX\n"
"8. КЛЮЧЕВЫЕ МЕТРИКИ:\n"
"   Revenue/Transaction / Cost/Transaction / Net Margin/Transaction\n"
"   Fraud Rate (норма <0.1%) / Chargeback Rate (норма <1%)"}
}

# ═══════════════════════════════════════════
#  ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ
# ═══════════════════════════════════════════
def generate_image(prompt_text, project_name):
    """Генерация изображения через DALL-E 3"""
    if not OPENAI_KEY:
        return None, "OpenAI ключ не настроен"
    try:
        oai = OpenAI(api_key=OPENAI_KEY)
        enhanced_prompt = (
            f"Professional business infographic for '{project_name}'. "
            f"{prompt_text}. "
            f"Modern fintech style, clean design, blue and gold colors, "
            f"Kazakhstan/Central Asia context, no text overlay, "
            f"suitable for business presentation."
        )
        response = oai.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        return response.data[0].url, None
    except Exception as e:
        return None, str(e)

async def send_project_image(task, analysis_summary):
    """Создать и отправить изображение для проекта"""
    if not OPENAI_KEY:
        return
    try:
        loop = asyncio.get_event_loop()
        image_prompt = (
            f"Business visualization: {task[:200]}. "
            f"Show the key concept as a modern infographic or diagram."
        )
        url, err = await loop.run_in_executor(
            None, generate_image, image_prompt, task[:50]
        )
        if url:
            await bot.send_photo(
                CHANNEL_ID,
                photo=url,
                caption=f"🎨 Визуализация проекта\n📝 {task[:100]}..."
            )
            log.info("Изображение отправлено")
        else:
            log.warning(f"Ошибка генерации изображения: {err}")
    except Exception as e:
        log.error(f"Ошибка отправки изображения: {e}")

# ═══════════════════════════════════════════
#  ПАМЯТЬ
# ═══════════════════════════════════════════
class Memory:
    def __init__(self):
        self.d = {"tasks":[],"total":0,"optimizations":[]}
        if MEMORY_FILE.exists():
            try: self.d = json.loads(MEMORY_FILE.read_text())
            except: pass
    def save(self): MEMORY_FILE.write_text(json.dumps(self.d,ensure_ascii=False,indent=2))
    def add(self, task, responses):
        self.d["total"] += 1
        self.d["tasks"].append({
            "id":self.d["total"],
            "ts":datetime.now().isoformat(),
            "task":task[:400],
            "s":{k:v[:200] for k,v in responses.items()}
        })
        if len(self.d["tasks"])>100: self.d["tasks"]=self.d["tasks"][-100:]
        self.save(); return self.d["total"]
    def need_opt(self): return self.d["total"]>0 and self.d["total"]%OPTIMIZE_EVERY==0
    def recent(self,n=15): return self.d["tasks"][-n:]
    def log_opt(self,eid,changed):
        self.d["optimizations"].append({"ts":datetime.now().isoformat(),"e":eid,"c":changed})
        self.save()

# ═══════════════════════════════════════════
#  ПРОМПТЫ
# ═══════════════════════════════════════════
class Prompts:
    def __init__(self):
        self.d = {}; self.v = 1
        if PROMPTS_FILE.exists():
            try:
                raw=json.loads(PROMPTS_FILE.read_text())
                self.d=raw.get("experts",{}); self.v=raw.get("version",1)
            except: pass
        for k,v in EXPERTS.items():
            if k not in self.d: self.d[k]=dict(v)
    def save(self):
        self.v+=1
        PROMPTS_FILE.write_text(json.dumps({
            "version":self.v,
            "updated":datetime.now().isoformat(),
            "experts":self.d
        },ensure_ascii=False,indent=2))
    def get(self,eid): return self.d.get(eid,EXPERTS.get(eid,{}))
    def update(self,eid,p):
        if eid in self.d: self.d[eid]["prompt"]=p; self.save()

# ═══════════════════════════════════════════
#  ОПТИМИЗАТОР
# ═══════════════════════════════════════════
class Optimizer:
    def __init__(self,c,p,m): self.c=c; self.p=p; self.m=m
    async def run(self):
        recent=self.m.recent(15)
        if len(recent)<3: return
        examples="\n".join([f"- {t['task'][:150]}" for t in recent])
        loop=asyncio.get_event_loop()
        await asyncio.gather(*[
            loop.run_in_executor(None,self._one,eid,examples)
            for eid in EXPERTS
        ])
        log.info("Оптимизация завершена")
    def _one(self,eid,examples):
        e=self.p.get(eid); old=e.get("prompt",""); name=e.get("name",eid)
        prompt=(
            f"Улучши промпт для роли '{name}'.\n"
            f"ТЕКУЩИЙ:\n{old}\n\n"
            f"ПОСЛЕДНИЕ ЗАДАЧИ:\n{examples}\n\n"
            f"Правила: сохрани КЗ/СНГ специализацию, структуру разделов, русский язык.\n"
            f"Верни ТОЛЬКО улучшенный промпт."
        )
        try:
            msg=self.c.messages.create(
                model="claude-opus-4-5",max_tokens=700,
                messages=[{"role":"user","content":prompt}]
            )
            new=msg.content[0].text.strip()
            changed=bool(new and new!=old and len(new)>80)
            if changed: self.p.update(eid,new); log.info(f"✓ {name} обновлён")
            self.m.log_opt(eid,changed)
        except Exception as ex: log.error(f"✗ {name}: {ex}")

# ═══════════════════════════════════════════
#  ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════
cc=anthropic.Anthropic(api_key=CLAUDE_KEY)
mem=Memory(); prm=Prompts(); opt=Optimizer(cc,prm,mem)
bot=Bot(token=BOT_TOKEN); dp=Dispatcher()

def call(eid,task):
    e=prm.get(eid)
    try:
        msg=cc.messages.create(
            model="claude-opus-4-5",max_tokens=900,
            system=e["prompt"],
            messages=[{"role":"user","content":task}]
        )
        return eid,msg.content[0].text
    except Exception as ex: return eid,f"❌ {ex}"

async def tg_send(text):
    while text:
        if len(text)<=4000: await bot.send_message(CHANNEL_ID,text); break
        sp=text.rfind("\n",0,4000)
        if sp==-1: sp=4000
        await bot.send_message(CHANNEL_ID,text[:sp])
        text=text[sp:].lstrip("\n"); await asyncio.sleep(0.4)

async def run_experts(task):
    loop=asyncio.get_event_loop()
    return dict(await asyncio.gather(*[
        loop.run_in_executor(None,call,eid,task)
        for eid in EXPERTS
    ]))

# ═══════════════════════════════════════════
#  ХЭНДЛЕРЫ
# ═══════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(m:Message):
    has_img = "✅" if OPENAI_KEY else "❌ (нужен OPENAI_KEY)"
    await m.answer(
        f"👋 *AI Team Bot v4.0*\n\n"
        f"🤖 15 экспертов · КЗ + СНГ\n"
        f"🏦 Финансовое право КЗ (новый эксперт)\n"
        f"🎨 Генерация картинок: {has_img}\n"
        f"🧠 Самообучение каждые {OPTIMIZE_EVERY} задач\n\n"
        f"Напишите задачу → ответы придут в канал.\n\n"
        f"/status /optimize /version /image",
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def cmd_status(m:Message):
    t=mem.d["total"]; o=len(mem.d["optimizations"])
    ch=sum(1 for x in mem.d["optimizations"] if x.get("c"))
    nxt=OPTIMIZE_EVERY-(t%OPTIMIZE_EVERY) if t%OPTIMIZE_EVERY else OPTIMIZE_EVERY
    await m.answer(
        f"📊 *Статус бота v4.0*\n\n"
        f"Задач обработано: {t}\n"
        f"Оптимизаций: {o}\n"
        f"Промптов улучшено: {ch}\n"
        f"До оптимизации: {nxt} задач\n"
        f"Версия промптов: v{prm.v}\n"
        f"Генерация картинок: {'✅' if OPENAI_KEY else '❌'}",
        parse_mode="Markdown"
    )

@dp.message(Command("optimize"))
async def cmd_optimize(m:Message):
    await m.answer("🔧 Оптимизирую промпты...")
    await opt.run()
    await m.answer(f"✅ Готово! Версия: v{prm.v}")

@dp.message(Command("version"))
async def cmd_version(m:Message):
    lines=[f"📝 *Промпты v{prm.v}*\n"]
    for eid in EXPERTS:
        e=prm.get(eid)
        lines.append(f"{e['emoji']} {e['name']}: {len(e.get('prompt',''))} симв.")
    await m.answer("\n".join(lines),parse_mode="Markdown")

@dp.message(Command("image"))
async def cmd_image(m:Message):
    if not OPENAI_KEY:
        await m.answer("❌ OPENAI_KEY не настроен в Variables Railway.")
        return
    text=m.text.replace("/image","").strip()
    if not text:
        await m.answer("Напишите: /image описание картинки")
        return
    await m.answer("🎨 Генерирую изображение...")
    loop=asyncio.get_event_loop()
    url,err=await loop.run_in_executor(None,generate_image,text,text[:30])
    if url:
        await bot.send_photo(CHANNEL_ID,photo=url,caption=f"🎨 {text[:100]}")
        await m.answer("✅ Изображение отправлено в канал!")
    else:
        await m.answer(f"❌ Ошибка: {err}")

@dp.message(F.text)
async def handle(m:Message):
    task=m.text.strip()
    if len(task)<5: await m.answer("Опишите задачу подробнее."); return
    await m.answer("⏳ Анализирую... ~60-90 сек.")
    try:
        await tg_send(
            f"⚡ AI TEAM BOARD v4.0\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 {task}\n\n"
            f"🔄 Анализируют 15 экспертов..."
        )
        resp=await run_experts(task)
        for eid,r in resp.items():
            e=prm.get(eid)
            await tg_send(f"{e['emoji']} {e['name']}\n{'─'*28}\n{r}")
            await asyncio.sleep(0.5)
        tid=mem.add(task,resp)
        await tg_send(
            f"✅ Анализ завершён · 15 экспертов\n"
            f"📌 Задача #{tid} · Промпты v{prm.v}"
        )
        # Генерация изображения если есть ключ
        if OPENAI_KEY:
            asyncio.create_task(send_project_image(task, resp.get("orchestrator",("",""))[1] if isinstance(resp.get("orchestrator"), tuple) else ""))
        await m.answer(f"✅ Готово! #{tid}")
        if mem.need_opt():
            asyncio.create_task(opt.run())
    except Exception as ex:
        log.error(f"Ошибка: {ex}"); await m.answer(f"❌ {ex}")

async def main():
    log.info(f"🚀 СТАРТ | BOT_TOKEN={'OK' if BOT_TOKEN else 'ПУСТО'} | CLAUDE={'OK' if CLAUDE_KEY else 'ПУСТО'} | CHANNEL={CHANNEL_ID}")
    log.info(f"🚀 AI Team Bot v4.0 | 15 экспертов | Задач: {mem.d['total']} | v{prm.v}")
    log.info(f"Генерация картинок: {'✅ включена' if OPENAI_KEY else '❌ нет OPENAI_KEY'}")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        log.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise

if __name__=="__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
