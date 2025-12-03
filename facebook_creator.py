import asyncio
import time
import random
import os
import sys
import requests
import re
from faker import Faker
from playwright.async_api import async_playwright, TimeoutError

# تهيئة مولد البيانات العشوائية
fake = Faker('en_US')

# نطاقات 1SecMail الموثوقة (لا تحتاج لملف domains.txt)
DOMAIN_LIST = ["1secmail.net", "1secmail.com", "1secmail.org"] 

# --- الدوال المساعدة ---

def load_data(filename):
    """تحميل البيانات من ملف user_agents.txt"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = [line.strip() for line in f if line.strip()]
            if not data:
                log_output(f"🛑 خطأ: الملف {filename} فارغ. يرجى ملئه!")
            return data
    except FileNotFoundError:
        log_output(f"🛑 خطأ: لم يتم العثور على الملف {filename}. تأكد من وجوده!")
        return []

def log_output(message):
    """طباعة الرسائل لتقرير GitHub Actions"""
    print(message, flush=True)

def generate_1secmail():
    """توليد إيميل عشوائي ونطاق عشوائي من نطاقات 1SecMail"""
    username = fake.word() + str(random.randint(100, 999))
    domain = random.choice(DOMAIN_LIST)
    return f"{username}@{domain}", username

async def fetch_confirmation_code(username, email, timeout=60):
    """الاتصال بـ 1SecMail API لجلب كود التفعيل"""
    start_time = time.time()
    domain = email.split("@")[1]

    # الانتظار الأولي الضروري
    await asyncio.sleep(random.randint(10, 20)) 
    
    log_output(f"📧  بدء البحث عن كود التفعيل لـ {email}...")

    while (time.time() - start_time) < timeout:
        try:
            # API لاستقبال الرسائل
            response = requests.get(f'https://www.1secmail.com/api/v1/?action=getMessages&login={username}&domain={domain}')
            messages = response.json()
            
            if messages:
                for msg in messages:
                    # جلب الرسالة وقراءتها
                    full_message_response = requests.get(f'https://www.1secmail.com/api/v1/?action=readMessage&login={username}&domain={domain}&id={msg["id"]}')
                    message_data = full_message_response.json()
                    
                    # التحقق من المرسل والمحتوى
                    if message_data.get('from', '').endswith('facebookmail.com') or 'facebook' in message_data.get('subject', '').lower():
                        body = message_data.get('body', '') + message_data.get('textBody', '')
                        # البحث عن كود مكون من 5 أرقام (سواء FB-XXXXX أو فقط XXXXX)
                        match = re.search(r'FB-(\d{5})|(\d{5})', body)
                        if match:
                            code = match.group(1) or match.group(2)
                            log_output(f"✅ تم استلام الكود: {code}")
                            return code
            
            await asyncio.sleep(5) 

        except Exception:
            await asyncio.sleep(5) 

    return None

# --- الدالة الرئيسية لإنشاء حساب واحد ---

async def create_facebook_account(p, user_agents, password):
    start_time = time.time()
    browser = None
    account_info = None
    username_1sec = None

    try:
        user_agent = random.choice(user_agents)
        email, username_1sec = generate_1secmail()
        
        first_name = fake.first_name()
        last_name = fake.last_name()
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=45) 
        
        browser = await p.chromium.launch(headless=True, args=[f'--user-agent={user_agent}'])
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        log_output(f"🤖  بدء التسجيل: {first_name} {last_name} | الإيميل: {email[:5]}... | UA: {user_agent[:20]}...")
        await page.goto("https://www.facebook.com/reg/")
        
        # محاكاة الإدخال البشري البطيء
        await page.fill('input[name="firstname"]', first_name, delay=random.randint(100, 300)); await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.fill('input[name="lastname"]', last_name, delay=random.randint(100, 300)); await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.fill('input[name="reg_email__"]', email, delay=random.randint(50, 150)); await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.fill('input[name="reg_email_confirmation__"]', email, delay=random.randint(50, 150)); await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.fill('input[name="reg_passwd__"]', password, delay=random.randint(150, 400)); await asyncio.sleep(random.uniform(1.0, 2.0))

        # اختيار تاريخ الميلاد والجنس
        await page.select_option('select[name="birthday_month"]', str(birth_date.month))
        await page.select_option('select[name="birthday_day"]', str(birth_date.day))
        await page.select_option('select[name="birthday_year"]', str(birth_date.year))
        gender_value = str(random.choice([1, 2])) 
        await page.click(f'input[type="radio"][value="{gender_value}"]'); await asyncio.sleep(random.uniform(2.0, 4.0))

        # محاكاة النقر على زر التسجيل
        await page.click('button[name="websubmit"]')
        log_output("⏳ تم إرسال طلب التسجيل... انتظار صفحة التأكيد...")
        
        try:
            await page.wait_for_selector('div:has-text("Enter the 5-digit code we sent to")', timeout=30000)
            status_message = "Code Requested"
        except TimeoutError:
            status_message = "Blocked_NoCodePage"

        if status_message == "Code Requested":
            log_output("✅  نجاح مبدئي: تم طلب كود التفعيل!")
            confirmation_code = await fetch_confirmation_code(username_1sec, email)
            
            if confirmation_code:
                await page.fill('input[name="code"]', confirmation_code)
                await page.click('button[value="1"]') 
                log_output("✨  تم تأكيد الحساب بنجاح!")
                status = "Successful"
            else:
                log_output("❌ فشل: لم يتم استلام كود التفعيل في الوقت المحدد.")
                status = "Failed_Code_Timeout"
        else:
            log_output("🚫 حظر فوري: فيسبوك رفض التسجيل قبل طلب الكود.")
            status = "Blocked_Immediately"

        account_info = f"{email}:{password}:{first_name} {last_name}"

    except Exception as e:
        log_output(f"❌ فشل: خطأ غير متوقع: {e}")
        status = "Failed_Unhandled_Error"
        account_info = f"{email}:{password}:{first_name} {last_name}"
        
    finally:
        if browser:
            await browser.close()
        return status, time.time() - start_time, account_info

# --- حلقة التشغيل الرئيسية ---

async def main_loop():
    log_output("\n" + "="*40)
    log_output("✨WELCOME ABDALLAH MONIR ✨")
    log_output("="*40)
    
    # قراءة المدخلات من متغيرات البيئة (GitHub Actions) أو السؤال المحلي
    num_accounts_str = os.environ.get('INPUT_NUM_ACCOUNTS')  
    password = os.environ.get('INPUT_PASSWORD')            

    try:
        if not num_accounts_str or not password:
            print("⚠️ المدخلات غير موجودة. الرجاء الإدخال يدوياً.")
            num_accounts = int(input("💡 كم عدد الحسابات التي تريد إنشائها؟ (رقم): "))
            password = input("🔑 أدخل كلمة المرور الموحدة للحسابات: ")
        else:
            num_accounts = int(num_accounts_str)
            log_output(f"✅ تم قراءة المدخلات: إنشاء {num_accounts} حساب.")

        if not password: return
            
    except ValueError:
        log_output("⚠️ يرجى إدخال رقم صحيح للحسابات. إلغاء العملية.")
        return

    # تحميل وكلاء المستخدم (الملف الوحيد المطلوب)
    user_agents = load_data('user_agents.txt')
    if not user_agents: return

    successful_count = 0
    failed_count = 0
    all_statuses = []
    
    # تهيئة ملفات المخرجات
    with open('successful_accounts.txt', 'w', encoding='utf-8') as f: f.write("EMAIL:PASSWORD:NAME\n")
    with open('failed_accounts.txt', 'w', encoding='utf-8') as f: f.write("STATUS:EMAIL:PASSWORD:NAME\n")
    
    async with async_playwright() as p:
        for i in range(1, num_accounts + 1):
            log_output(f"\n--- 🟢 بدء الحساب رقم {i} من أصل {num_accounts} ---")
            status, duration, info = await create_facebook_account(p, user_agents, password)
            all_statuses.append((status, duration, info))

            if status == "Successful":
                successful_count += 1
                log_output(f"🎉 تم بنجاح: الحساب {i} استغرق {duration:.2f} ثانية.")
                with open('successful_accounts.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{info}\n")
            else:
                failed_count += 1
                log_output(f"❌ فشل/حظر: الحساب {i} استغرق {duration:.2f} ثانية. الحالة: {status}")
                with open('failed_accounts.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{status}:{info if info else 'Unknown'}\n")
            
            # تقرير التقدم الفوري
            log_output(f"| حالة التشغيل: ناجح: {successful_count} | فاشل: {failed_count} |")
            log_output("-" * 30)

            await asyncio.sleep(random.uniform(5, 10))

    # التقرير النهائي (في نهاية التشغيل)
    total_time = sum(d for s, d, i in all_statuses)
    avg_time_per_account = total_time / successful_count if successful_count else 0
    accounts_per_hour = (3600 / avg_time_per_account) if avg_time_per_account > 0 else 0
    
    log_output("\n" + "="*40)
    log_output("📋 تقرير التشغيل النهائي")
    log_output(f"الحسابات الناجحة: {successful_count}")
    log_output(f"الحسابات الفاشلة/المحظورة: {failed_count}")
    log_output(f"متوسط وقت الحساب الواحد: {avg_time_per_account:.2f} ثانية")
    log_output(f"الإنتاجية المُقدرة (في الساعة): {accounts_per_hour:.2f} حساب")
    log_output("تم حفظ النتائج في successful_accounts.txt و failed_accounts.txt.")
    log_output("="*40)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_output("\nتم إيقاف التشغيل يدوياً.")
        sys.exit(0)