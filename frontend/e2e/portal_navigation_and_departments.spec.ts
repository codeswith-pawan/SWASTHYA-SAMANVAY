import { test, expect } from "@playwright/test";

test.describe("Government Portal Redesign - Navigation & Department Journey", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("1. Landing Page renders government branding and hero sections", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/ArogyaSetu Grid/);

    // Official Header Banner
    await expect(page.locator("text=Grid Online").first()).toBeVisible();
    await expect(page.locator("text=ArogyaSetu Grid").first()).toBeVisible();
    await expect(page.locator("text=1075").first()).toBeVisible();

    // Hero Section
    await expect(
      page.locator("h1:has-text('Integrated Hospital Bed Coordination & Emergency Patient Referral Portal')")
    ).toBeVisible();
    await expect(
      page.locator(
        "text=A unified digital platform connecting frontline hospitals"
      )
    ).toBeVisible();

    // CTAs in Hero
    await expect(page.locator("section a:has-text('Register Hospital')").first()).toBeVisible();
    await expect(page.locator("section a:has-text('Track Application')").first()).toBeVisible();
    await expect(page.locator("section a:has-text('Staff / Department Login')").first()).toBeVisible();

    // Meaningful Sections
    await expect(page.locator("text=Departmental Sign-In Gateways")).toBeVisible();
    await expect(page.locator("text=Access Your Healthcare Jurisdiction")).toBeVisible();
    await expect(page.locator("text=How ArogyaSetu Grid Operates")).toBeVisible();
  });

  test("2. Explore Portal navigation opens Department Selection Page", async ({ page }) => {
    await page.goto("/");
    // Click the hero Staff / Department Login CTA
    await page.locator("section a:has-text('Staff / Department Login')").first().click();

    await expect(page).toHaveURL(/\/portal$/);
    await expect(page.locator("h1:has-text('Select Your Department')")).toBeVisible();
    await expect(
      page.locator("text=Choose your authorized department to access the portal.")
    ).toBeVisible();

    // 4 Department Cards
    await expect(page.locator("h2:has-text('HOSPITAL PORTAL')")).toBeVisible();
    await expect(page.locator("h2:has-text('DISTRICT PORTAL')")).toBeVisible();
    await expect(page.locator("h2:has-text('STATE PORTAL')")).toBeVisible();
    await expect(page.locator("h2:has-text('CENTRAL PORTAL')")).toBeVisible();

    // Key Features in Cards
    await expect(page.locator("text=Bed and inventory management")).toBeVisible();
    await expect(page.locator("text=District hospital monitoring")).toBeVisible();
    await expect(page.locator("text=State hospital administration")).toBeVisible();
    await expect(page.locator("text=National-level monitoring")).toBeVisible();
  });

  test("3. Department cards navigate to dedicated login experiences and back", async ({ page }) => {
    await page.goto("/portal");

    // Hospital Login
    await page.locator("a:has-text('Login to Hospital')").click();
    await expect(page).toHaveURL(/\/portal\/hospital\/login$/);
    await expect(page.locator("h1:has-text('Hospital Operations Login')")).toBeVisible();
    await expect(page.locator("input[placeholder*='gh00046']")).toBeVisible();
    await expect(page.locator("input[placeholder*='password']")).toBeVisible();

    // Back navigation to /portal
    await page.locator("a:has-text('Back to Department Selection')").click();
    await expect(page).toHaveURL(/\/portal$/);

    // District Login
    await page.locator("a:has-text('Login to District')").click();
    await expect(page).toHaveURL(/\/portal\/district\/login$/);
    await expect(page.locator("h1:has-text('District Health Authority Login')")).toBeVisible();

    await page.locator("a:has-text('Back to Department Selection')").click();
    await expect(page).toHaveURL(/\/portal$/);

    // State Login
    await page.locator("a:has-text('Login to State')").click();
    await expect(page).toHaveURL(/\/portal\/state\/login$/);
    await expect(page.locator("h1:has-text('State Health Directorate Login')")).toBeVisible();

    await page.locator("a:has-text('Back to Department Selection')").click();
    await expect(page).toHaveURL(/\/portal$/);

    // Central Login
    await page.locator("a:has-text('Login to Central')").click();
    await expect(page).toHaveURL(/\/portal\/central\/login$/);
    await expect(page.locator("h1:has-text('Central Health Command Login')")).toBeVisible();
  });

  test("4. Dedicated Department Login enforces Role Mismatch protection", async ({ page }) => {
    // Attempting to log into Hospital Portal using District Admin credentials
    await page.goto("/portal/hospital/login");

    await page.locator("input[placeholder*='gh00046']").fill("amritsar_district_admin");
    await page.locator("input[placeholder*='password']").fill("district123");
    await page.locator("button:has-text('Sign In to Hospital Portal')").click();

    // Verify Role Mismatch Alert
    await expect(page.locator("text=Department Role Mismatch")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=DISTRICT_ADMIN")).toBeVisible();
    await expect(page.locator("a:has-text('Proceed to District Portal')")).toBeVisible();

    // Click redirect to proper authorized portal
    await page.locator("a:has-text('Proceed to District Portal')").click();
    await expect(page).toHaveURL(/\/portal\/district\/login$/);
  });

  test("5. Successful Department Login routes to authorized Role Dashboard", async ({ page }) => {
    await page.goto("/portal/district/login");

    await page.locator("input[placeholder*='amritsar_district_admin']").fill("amritsar_district_admin");
    await page.locator("input[placeholder*='password']").fill("district123");
    await page.locator("button:has-text('Sign In to District Portal')").click();

    // Verify authorized dashboard is shown
    await expect(page.locator("button:has-text('Sign Out')").first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=District Administration").first()).toBeVisible();
    await expect(page.locator("text=Amritsar Health Operations").first()).toBeVisible();

    // Clean sign out
    await page.locator("button:has-text('Sign Out')").first().click();
    await page.waitForTimeout(500);
  });

  test("6. Public links provide direct access to Hospital Registration & Track Application", async ({ page }) => {
    await page.goto("/");

    // Register Hospital from Hero Section
    await page.locator("section a:has-text('Register Hospital')").first().click();
    await expect(page).toHaveURL(/\/register\/hospital$/);

    // Back to home & Track Application from Hero Section
    await page.goto("/");
    await page.locator("section a:has-text('Track Application')").first().click();
    await expect(page).toHaveURL(/\/application\/status$/);
  });

  test("7. Bilingual English ↔ हिन्दी switcher updates public portal and persists across routes", async ({ page }) => {
    await page.goto("/");

    // Default English state
    await expect(
      page.locator("h1:has-text('Integrated Hospital Bed Coordination & Emergency Patient Referral Portal')")
    ).toBeVisible();
    await expect(page.locator("text=Emergency Ambulance: 108").first()).toBeVisible();

    // Toggle to हिन्दी
    await page.locator("button:has-text('हिन्दी')").first().click();

    // Verify instant Hindi translation on Home page
    await expect(
      page.locator("h1:has-text('एकीकृत अस्पताल बेड समन्वय एवं आपातकालीन मरीज रेफरल पोर्टल')")
    ).toBeVisible();
    await expect(page.locator("text=आपातकालीन एम्बुलेंस: 108").first()).toBeVisible();
    await expect(page.locator("header a:has-text('हमारे बारे में')")).toBeVisible();
    await expect(page.locator("header a:has-text('सेवाएं')")).toBeVisible();
    await expect(page.locator("header a:has-text('अस्पताल नेटवर्क')")).toBeVisible();

    // Navigate to /about and verify persistence
    await page.locator("header a:has-text('हमारे बारे में')").click();
    await expect(page).toHaveURL(/\/about$/);
    await expect(page.locator("h1:has-text('आरोग्यसेतु ग्रिड के बारे में')")).toBeVisible();
    await expect(page.locator("text=हमारा लक्ष्य (Core Mission)")).toBeVisible();

    // Navigate to /portal and verify persistence
    await page.goto("/portal");
    await expect(page.locator("h1:has-text('अपने विभाग का चयन करें')")).toBeVisible();
    await expect(page.locator("h2:has-text('अस्पताल पोर्टल')")).toBeVisible();

    // Switch back to English
    await page.locator("button:has-text('English')").first().click();
    await expect(page.locator("h1:has-text('Select Your Department')")).toBeVisible();
    await expect(page.locator("h2:has-text('HOSPITAL PORTAL')")).toBeVisible();
  });

  test("8. Footer policy links navigate to dedicated bilingual policy pages", async ({ page }) => {
    await page.goto("/");

    // Click Security Policy
    await page.locator("footer a:has-text('Security Policy')").first().click();
    await expect(page).toHaveURL(/\/policies\/security$/);
    await expect(page.locator("h1:has-text('Security & Patient Privacy Policy')")).toBeVisible();

    // Click Terms of Service
    await page.locator("footer a:has-text('Terms of Service')").first().click();
    await expect(page).toHaveURL(/\/policies\/terms$/);
    await expect(page.locator("h1:has-text('Terms of Service & Operational Rules')")).toBeVisible();

    // Click Jurisdictional Governance
    await page.locator("footer a:has-text('Jurisdictional Governance')").first().click();
    await expect(page).toHaveURL(/\/policies\/governance$/);
    await expect(page.locator("h1:has-text('Jurisdictional Governance & Administrative Framework')")).toBeVisible();

    // Click Inter-Hospital SLAs
    await page.locator("footer a:has-text('Inter-Hospital SLAs')").first().click();
    await expect(page).toHaveURL(/\/policies\/sla$/);
    await expect(page.locator("h1:has-text('Inter-Hospital Service Level Agreements (SLA)')")).toBeVisible();
  });
});
