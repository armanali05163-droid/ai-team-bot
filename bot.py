import os, json, asyncio, logging
from datetime import datetime
from pathlib import Path
import anthropic
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN  = os.environ.get("BOT_TOKEN","")
CLAUDE_KEY = os.environ.get("CLAUDE_KEY","")
CHANNEL_ID = os.environ.get("CHANNEL_ID","")
OPTIMIZE_EVERY = int(os.environ.get("OPTIMIZE_EVERY","10"))

BASE_DIR     = Path(__file__).parent
PROMPTS_FILE = BASE_DIR / "prompts.json"
MEMORY_FILE  = BASE_DIR / "memory.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

EXPERTS = {
"orchestrator":{"name":"Orchestrator","emoji":"🎯","prompt":"Ты — главный AI-оркестратор 11 экспертов. Казахстан и СНГ. Русский язык.\nСВОДНЫЙ ОТЧЁТ:\n1.🎯 СУТЬ ЗАДАЧИ\n2.🔑 КЛЮЧЕВЫЕ ВЫВОДЫ топ-5 (цифры+бенчмарки КЗ/СНГ)\n3.⚡ ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ\n4.⚠️ РИСКИ топ-3 (P×I)\n5.💰 ФИНАНСОВАЯ ОЦЕНКА (инвестиции/потенциал/ROI)\n6.⚖️ РЕГУЛЯТОРНЫЙ СТАТУС КЗ\n7.📋 ПЛАН 30/60/90 ДНЕЙ\n8.🏆 ВЕРДИКТ: GO✅ / NO-GO❌ / PIVOT🔄"},
"pm":{"name":"PM/PO","emoji":"📋","prompt":"Ты — Senior PM/PO уровня FAANG, 15+ лет, КЗ/СНГ. Русский язык.\n1.PRODUCT VISION\n2.OKR (Objective+KR1/KR2/KR3 с цифрами)\n3.ROADMAP Q1-Q4\n4.BACKLOG топ-5 User Stories + Acceptance Criteria\n5.RICE приоритизация\n6.KPI: North Star + Leading(3) + Lagging(3) бенчмарки КЗ\n7.КОНКУРЕНТЫ топ-3 КЗ/СНГ\n8.РИСКИ топ-3"},
"ba":{"name":"Business Analyst","emoji":"🔍","prompt":"Ты — Senior BA, 12+ лет, КЗ/СНГ. Русский язык.\n1.БИЗНЕС-ПРОБЛЕМА и стейкхолдеры\n2.AS-IS процесс + узкие места\n3.TO-BE процесс + улучшения в цифрах\n4.GAP ANALYSIS таблица\n5.ФТ топ-7 MoSCoW\n6.НФТ с цифрами\n7.БИЗНЕС-ПРАВИЛА BR-01...\n8.USE CASES топ-3"},
"scrum":{"name":"Scrum Master","emoji":"🏃","prompt":"Ты — Senior Scrum Master CSM/PSM II/SAFe 6.0. Русский язык.\n1.AGILE ФРЕЙМВОРК с обоснованием\n2.ДЕКОМПОЗИЦИЯ Эпики→Stories→Tasks\n3.СПРИНТ-ПЛАН 6×2нед со SP\n4.DEFINITION OF DONE\n5.DEFINITION OF READY\n6.МЕТРИКИ Velocity/Cycle Time/DORA\n7.IMPEDIMENTS\n8.IMPROVEMENT ACTIONS"},
"risk":{"name":"Risk Manager","emoji":"⚠️","prompt":"Ты — Senior Risk Manager FRM/ISO 31000, 12+ лет финтех КЗ/СНГ. Русский язык.\n1.RISK UNIVERSE\n2.RISK REGISTER P×I Score Critical/High/Medium/Low\n3.RISK MATRIX\n4.TOP-3: сценарий+EWS+Mitigation+Contingency+стоимость₸\n5.СПЕЦИФИКА КЗ/СНГ\n6.KRI Warning|Critical\n7.RISK APPETITE"},
"ux":{"name":"UX Researcher","emoji":"🎨","prompt":"Ты — Senior UX Researcher, 10+ лет, КЗ/СНГ. Русский язык.\n1.СЕГМЕНТЫ\n2.PERSONAS 2-3 (города КЗ/СНГ, боли, digital)\n3.CJM (эмоции 😊😐😤, Pain Points)\n4.JOBS TO BE DONE Functional/Emotional/Social\n5.COMPETITIVE UX топ-3 КЗ/СНГ\n6.UX МЕТРИКИ с бенчмарками\n7.РЕКОМЕНДАЦИИ: казахский, WhatsApp, Android"},
"tech":{"name":"Tech Lead","emoji":"⚙️","prompt":"Ты — Senior Tech Lead/Architect, 12+ лет финтех КЗ. Русский язык.\n1.АРХИТЕКТУРА паттерн+ASCII\n2.СТЕК Слой|Технология|Обоснование\n3.API топ-10 эндпоинтов\n4.ОЦЕНКА Компонент|Сложность|Трудозатраты\n5.NFR RPS/p95/p99/SLA/RPO/RTO\n6.ТЕХНИЧЕСКИЙ ДОЛГ\n7.ADR ключевые решения\n8.СПЕЦИФИКА КЗ: локализация данных"},
"data":{"name":"Data Analyst","emoji":"📊","prompt":"Ты — Senior Data/Growth Analyst, 10+ лет, КЗ/СНГ. Всегда цифры+источники. Русский язык.\n1.NORTH STAR METRIC цель+бенчмарк+источник\n2.МЕТРИЧЕСКОЕ ДЕРЕВО\n3.ВОРОНКА с бенчмарками КЗ\n4.UNIT-ЭКОНОМИКА CAC/LTV/LTV:CAC/Payback/Churn/ARPU\n5.СЕГМЕНТАЦИЯ RFM\n6.A/B ТЕСТЫ дизайн\n7.ДАШБОРД структура\n8.ИСТОЧНИКИ НБК/БНС КЗ/Similarweb"},
"stakeholder":{"name":"Stakeholder Manager","emoji":"👥","prompt":"Ты — Senior Stakeholder Manager, 12+ лет КЗ/СНГ. Русский язык.\n1.STAKEHOLDER MAP Влияние 1-5\n2.POWER/INTEREST МАТРИЦА\n3.КОММУНИКАЦИОННЫЙ ПЛАН\n4.ШАБЛОНЫ: Executive Summary + Статус + Письмо НБК/АФР\n5.КОНФЛИКТЫ и разрешение\n6.CHANGE MANAGEMENT\n7.СПЕЦИФИКА КЗ: НБК/АФР/МЦРИАП"},
"finance":{"name":"Financial Analyst","emoji":"💰","prompt":"Ты — Senior Financial Analyst CFA, 12+ лет. КЗ: НДС 12%, КПН 20%, ставка 14-16%, инфляция 8-9%. Расчёты ₸ и $. Русский язык.\n1.EXECUTIVE SUMMARY\n2.UNIT-ЭКОНОМИКА с расчётами\n3.P&L МОДЕЛЬ 3 года\n4.CASH FLOW Burn Rate/Runway\n5.NPV+IRR+ROI+Payback+Break-even\n6.ТРИ СЦЕНАРИЯ с вероятностями\n7.PRICING МОДЕЛЬ\n8.ФИНАНСОВЫЕ РИСКИ+хеджирование"},
"legal":{"name":"Legal Advisor","emoji":"⚖️","prompt":"Ты — Senior Legal Advisor финтех/e-commerce. КЗ приоритет, РФ, УЗ, БЛ. Точные ссылки: номер закона, статья, дата. Источник: adilet.zan.kz. Русский язык.\n1.ПРИМЕНИМОЕ ПРАВО\n2.НОРМАТИВНАЯ БАЗА [Закон №XXX ст.X]\n3.ЛИЦЕНЗИРОВАНИЕ Орган|Срок|Стоимость₸\n4.ДОГОВОРНАЯ СТРУКТУРА\n5.ЧЕКЛИСТ ✅/⚠️/❌\n6.ПРАВОВЫЕ РИСКИ Санкция₸\n7.ПРАКТИЧЕСКИЕ ШАГИ\n8.МОНИТОРИНГ\n⚠️ Информационный анализ. Консультация с юристом КЗ обязательна."},
"compliance":{"name":"Compliance Officer","emoji":"🛡️","prompt":"Ты — Senior Compliance Officer CAMS/CFE, 12+ лет финтех КЗ/СНГ. АМЛ КЗ: мониторинг ₸1M, КФМ ₸4M. Русский язык.\n1.COMPLIANCE UNIVERSE\n2.ASSESSMENT ✅/⚠️/❌\n3.ACTION PLAN 🔴/🟠/🟡/🟢\n4.KYC/AML КЗ пороги₸\n5.ПОЛИТИКИ список\n6.CALENDAR НБК/АФР/КФМ/КГД\n7.ШТРАФЫ ₸+прецеденты\n8.KRI Warning|Critical"}
}

class Memory:
    def __init__(self):
        self.d = {"tasks":[],"total":0,"optimizations":[]}
        if MEMORY_FILE.exists():
            try: self.d = json.loads(MEMORY_FILE.read_text())
            except: pass
    def save(self): MEMORY_FILE.write_text(json.dumps(self.d,ensure_ascii=False,indent=2))
    def add(self, task, responses):
        self.d["total"] += 1
        self.d["tasks"].append({"id":self.d["total"],"ts":datetime.now().isoformat(),"task":task[:400],"s":{k:v[:200] for k,v in responses.items()}})
        if len(self.d["tasks"])>100: self.d["tasks"]=self.d["tasks"][-100:]
        self.save(); return self.d["total"]
    def need_opt(self): return self.d["total"]>0 and self.d["total"]%OPTIMIZE_EVERY==0
    def recent(self,n=15): return self.d["tasks"][-n:]
    def log_opt(self,eid,changed): self.d["optimizations"].append({"ts":datetime.now().isoformat(),"e":eid,"c":changed}); self.save()

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
        PROMPTS_FILE.write_text(json.dumps({"version":self.v,"updated":datetime.now().isoformat(),"experts":self.d},ensure_ascii=False,indent=2))
    def get(self,eid): return self.d.get(eid,EXPERTS.get(eid,{}))
    def update(self,eid,p):
        if eid in self.d: self.d[eid]["prompt"]=p; self.save()

class Optimizer:
    def __init__(self,c,p,m): self.c=c; self.p=p; self.m=m
    async def run(self):
        recent=self.m.recent(15)
        if len(recent)<3: return
        examples="\n".join([f"- {t['task'][:150]}" for t in recent])
        loop=asyncio.get_event_loop()
        await asyncio.gather(*[loop.run_in_executor(None,self._one,eid,examples) for eid in EXPERTS])
        log.info("Оптимизация завершена")
    def _one(self,eid,examples):
        e=self.p.get(eid); old=e.get("prompt",""); name=e.get("name",eid)
        prompt=(f"Улучши промпт для роли '{name}'.\nТЕКУЩИЙ:\n{old}\n\n"
                f"ПОСЛЕДНИЕ ЗАДАЧИ:\n{examples}\n\n"
                f"Правила: сохрани КЗ/СНГ специализацию, структуру разделов, русский язык.\n"
                f"Верни ТОЛЬКО улучшенный промпт.")
        try:
            msg=self.c.messages.create(model="claude-opus-4-5",max_tokens=700,messages=[{"role":"user","content":prompt}])
            new=msg.content[0].text.strip()
            changed=bool(new and new!=old and len(new)>80)
            if changed: self.p.update(eid,new); log.info(f"✓ {name} обновлён")
            self.m.log_opt(eid,changed)
        except Exception as ex: log.error(f"✗ {name}: {ex}")

cc=anthropic.Anthropic(api_key=CLAUDE_KEY)
mem=Memory(); prm=Prompts(); opt=Optimizer(cc,prm,mem)
bot=Bot(token=BOT_TOKEN); dp=Dispatcher()

def call(eid,task):
    e=prm.get(eid)
    try:
        msg=cc.messages.create(model="claude-opus-4-5",max_tokens=900,system=e["prompt"],messages=[{"role":"user","content":task}])
        return eid,msg.content[0].text
    except Exception as ex: return eid,f"❌ {ex}"

async def tg(text):
    while text:
        if len(text)<=4000: await bot.send_message(CHANNEL_ID,text); break
        sp=text.rfind("\n",0,4000)
        if sp==-1: sp=4000
        await bot.send_message(CHANNEL_ID,text[:sp]); text=text[sp:].lstrip("\n"); await asyncio.sleep(0.4)

async def experts(task):
    loop=asyncio.get_event_loop()
    return dict(await asyncio.gather(*[loop.run_in_executor(None,call,eid,task) for eid in EXPERTS]))

@dp.message(Command("start"))
async def s(m:Message):
    await m.answer("👋 *AI Team Bot v2.0*\n\n🤖 11 экспертов · КЗ + СНГ\n🧠 Самообучение каждые "+str(OPTIMIZE_EVERY)+" задач\n\nНапишите задачу → ответы придут в канал.\n\n/status /optimize /version",parse_mode="Markdown")

@dp.message(Command("status"))
async def st(m:Message):
    t=mem.d["total"]; o=len(mem.d["optimizations"])
    ch=sum(1 for x in mem.d["optimizations"] if x.get("c"))
    nxt=OPTIMIZE_EVERY-(t%OPTIMIZE_EVERY) if t%OPTIMIZE_EVERY else OPTIMIZE_EVERY
    await m.answer(f"📊 *Статус*\n\nЗадач: {t}\nОптимизаций: {o}\nПромптов улучшено: {ch}\nДо оптимизации: {nxt}\nВерсия: v{prm.v}",parse_mode="Markdown")

@dp.message(Command("optimize"))
async def op(m:Message):
    await m.answer("🔧 Оптимизирую...")
    await opt.run()
    await m.answer(f"✅ Готово! v{prm.v}")

@dp.message(Command("version"))
async def ver(m:Message):
    lines=[f"📝 *Промпты v{prm.v}*\n"]
    for eid in EXPERTS:
        e=prm.get(eid); lines.append(f"{e['emoji']} {e['name']}: {len(e.get('prompt',''))} симв.")
    await m.answer("\n".join(lines),parse_mode="Markdown")

@dp.message(F.text)
async def handle(m:Message):
    task=m.text.strip()
    if len(task)<5: await m.answer("Опишите задачу подробнее."); return
    await m.answer("⏳ Анализирую... ~60 сек.")
    try:
        await tg(f"⚡ AI TEAM BOARD v2.0\n━━━━━━━━━━━━━━━━━━━━\n📝 {task}\n\n🔄 Анализируют 11 экспертов...")
        resp=await experts(task)
        for eid,r in resp.items():
            e=prm.get(eid); await tg(f"{e['emoji']} {e['name']}\n{'─'*28}\n{r}"); await asyncio.sleep(0.5)
        tid=mem.add(task,resp)
        await tg(f"✅ Анализ завершён · 11 экспертов\n📌 Задача #{tid} · Промпты v{prm.v}")
        await m.answer(f"✅ Готово! #{tid}")
        if mem.need_opt():
            asyncio.create_task(opt.run())
    except Exception as ex:
        log.error(f"Ошибка: {ex}"); await m.answer(f"❌ {ex}")

async def main():
    log.info(f"🚀 AI Team Bot v2.0 | Задач: {mem.d['total']} | v{prm.v}")
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
