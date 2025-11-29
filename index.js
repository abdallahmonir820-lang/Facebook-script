const puppeteer = require('puppeteer');
const fs = require('fs/promises');

// يمكنك تغيير عدد الحسابات المطلوبة هنا
const ACCOUNTS_TO_CREATE = 5; 
const OUTPUT_FILE = 'accounts_details.txt';

async function createAccount(browser) {
    const page = await browser.newPage();
    try {
        // 1. الانتقال إلى صفحة التسجيل
        await page.goto('https://www.facebook.com/reg/', { waitUntil: 'domcontentloaded' });

        // 2. توليد بيانات وهمية (يجب عليك استبدال هذه ببيانات حقيقية أو مولد)
        const firstName = `TestUser${Date.now().toString().slice(-4)}`;
        const lastName = 'Script';
        const email = `${firstName.toLowerCase()}@example.com`; // يجب استبدال هذا ببريد حقيقي أو مؤقت

        // 3. ملء نموذج التسجيل
        await page.type('#day', '15');
        await page.type('#month', 'Apr');
        await page.type('#year', '1990');
        await page.type('[name="firstname"]', firstName);
        await page.type('[name="lastname"]', lastName);
        await page.type('[name="reg_email__"]', email); 
        await page.type('[name="reg_email_confirmation__"]', email);
        await page.type('[name="reg_passwd__"]', 'StrongPass123!');
        
        // اختيار الجنس (ذكر: 2، أنثى: 1)
        await page.click('input[name="sex"][value="2"]'); 

        // 4. الضغط على زر التسجيل
        await page.click('#u_0_s_Jp'); // يجب التحقق من مُعرف الزر #u_0_s_Jp في الواجهة الحالية

        // 5. انتظار عملية التحقق (يختلف من نسخة لأخرى)
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });

        // 6. التحقق من نجاح العملية (قد تحتاج إلى تعديل هذا بناءً على خطوات فيسبوك الحالية)
        const currentUrl = page.url();
        if (currentUrl.includes('code_sentry')) {
            console.log(`[خطأ] العملية توقفت عند صفحة التحقق من البريد: ${email}`);
            return null;
        }

        console.log(`[نجاح] تم إنشاء حساب: ${firstName} ${lastName}`);
        return { firstName, lastName, email, password: 'StrongPass123!' };

    } catch (error) {
        console.error(`[خطأ] فشلت عملية إنشاء حساب لسبب ما: ${error.message}`);
        return null;
    } finally {
        await page.close();
    }
}

async function main() {
    console.log("--- بدء عملية إنشاء وتفعيل الحسابات (Puppeteer/Codespaces) ---");
    let browser;
    try {
        // إعداد المتصفح للعمل في بيئة Linux على Codespaces
        browser = await puppeteer.launch({
            headless: true,
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process', // يقلل من استهلاك الذاكرة
                '--disable-gpu'
            ]
        });

        const createdAccounts = [];
        let successfulCount = 0;

        for (let i = 0; i < ACCOUNTS_TO_CREATE; i++) {
            console.log(`\n--- محاولة إنشاء الحساب رقم ${i + 1} ---`);
            const account = await createAccount(browser);
            if (account) {
                createdAccounts.push(account);
                successfulCount++;
                // انتظار بين الحسابات لتجنب الحظر
                await new Promise(resolve => setTimeout(resolve, 5000)); 
            }
        }

        await browser.close();

        // حفظ تفاصيل الحسابات في ملف
        if (createdAccounts.length > 0) {
            const content = createdAccounts.map(acc => 
                `الاسم: ${acc.firstName} ${acc.lastName}, البريد: ${acc.email}, كلمة المرور: ${acc.password}`
            ).join('\n');
            await fs.writeFile(OUTPUT_FILE, content);
            
            console.log(`========================================`);
            console.log(`تم حفظ تفاصيل ${successfulCount} حساب بنجاح.`);
            console.log(`توصيل الحسابات في الملف ${OUTPUT_FILE}`);
            console.log(`========================================`);
        }

    } catch (err) {
        console.error("خطأ حرج في التطبيق:", err);
        if (browser) await browser.close();
    }
}

main().catch(err => {
    console.error("خطأ حرج في التطبيق:", err); 
});
