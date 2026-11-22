import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

const runHelper = (cmd: string, arg: string): string => {
  try {
    return execSync(`cd .. && .venv/bin/python e2e_db_helper.py ${cmd} "${arg}"`).toString().trim();
  } catch (err: any) {
    throw new Error(`Helper failed for ${cmd} ${arg}: ${err.message}`);
  }
};

const TEST_EMAIL = `nodal_amritsar_${Date.now()}@gov.in`;
let APP_NUMBER = "";
let TRACKING_TOKEN = "";
let PROVISIONED_USERNAME = "";

const signIn = async (page: any, username: string, pass: string) => {
  let portalUrl = "/portal/district/login";
  if (username.startsWith("gh") || username.toLowerCase().includes("hosp")) {
    portalUrl = "/portal/hospital/login";
  } else if (username.includes("district")) {
    portalUrl = "/portal/district/login";
  } else if (username.includes("state") || username.includes("punjab")) {
    portalUrl = "/portal/state/login";
  } else if (username.includes("central")) {
    portalUrl = "/portal/central/login";
  }

  await page.goto(portalUrl);
  await page.locator("input[type='text']").fill(username);
  await page.locator("input[type='password']").fill(pass);
  const submitBtn = page.locator("button[type='submit']");
  await submitBtn.scrollIntoViewIfNeeded();
  await submitBtn.click({ force: true });
  await expect(page.locator("button:has-text('Sign Out')")).toBeVisible({ timeout: 15000 });
};

const signOut = async (page: any) => {
  await page.goto("/");
  const signOutBtn = page.locator("button:has-text('Sign Out')");
  if (await signOutBtn.count() > 0) {
    await signOutBtn.first().click({ force: true });
    await page.waitForTimeout(500);
  }
};

const openDossier = async (page: any, appNum: string) => {
  await page.locator("input[placeholder*='Search by application']").fill(appNum);
  await page.waitForTimeout(600);
  const row = page.locator(`tr:has-text('${appNum}')`).first();
  await expect(row).toBeVisible({ timeout: 15000 });
  await row.scrollIntoViewIfNeeded();
  // Click either the Review Dossier button or the row
  const btn = row.locator("button:has-text('Review Dossier')");
  if (await btn.count() > 0) {
    await btn.scrollIntoViewIfNeeded();
    await btn.click({ force: true });
  } else {
    await row.click({ force: true });
  }
};

test.describe.serial("Phase 2D End-to-End Browser Workflows", () => {
  test("1. Applicant Registration & Submission Workflow", async ({ page }) => {
    await page.goto("/register/hospital");
    await expect(page).toHaveTitle(/ArogyaSetu Grid/);
    await expect(page.locator("text=Hospital Onboarding & Accreditation")).toBeVisible({ timeout: 15000 });

    // Step 1: Physical Infrastructure
    await page.locator("input[placeholder*='Guru Nanak Dev']").fill("AIIMS Amritsar Annex Super Specialty");
    await page.locator("select").nth(0).selectOption("Punjab");
    await page.locator("select").nth(1).selectOption("Amritsar");
    await page.locator("input[placeholder*='Amritsar']").fill("Amritsar");
    await page.locator("input[placeholder*='143001']").fill("143001");
    await page.locator("input[placeholder*='Majitha Road']").fill("Circular Road, Near Medical College");

    const bedInputs = page.locator("input[type='number']");
    await bedInputs.nth(0).fill("150"); // Total beds
    await bedInputs.nth(1).fill("30");  // ICU beds
    await bedInputs.nth(2).fill("20");  // Emergency beds
    await bedInputs.nth(3).fill("500"); // Oxygen capacity
    await bedInputs.nth(4).fill("15");  // Ventilators

    const btn1 = page.locator("button:has-text('Proceed to Contact & Verification')");
    await btn1.scrollIntoViewIfNeeded();
    await btn1.click({ force: true });

    // Step 2: Nodal Officer & Contact Verification
    await expect(page.locator("text=Designated Nodal Officer & Contact")).toBeVisible();
    await page.locator("input[placeholder*='Dr. Harpreet Singh']").fill("Dr. Harpreet Singh");
    await page.locator("input[placeholder*='Chief Medical Superintendent']").fill("Chief Medical Superintendent");
    await page.locator("input[placeholder*='nodal.hospital']").fill(TEST_EMAIL);
    await page.locator("input[placeholder*='98765 43210']").fill("9876543210");

    await page.locator("button:has-text('Verify Email')").click();
    await expect(page.locator("text=Email Verification")).toBeVisible();

    await page.waitForTimeout(1000);
    const otp = runHelper("get-otp", TEST_EMAIL);
    expect(otp).toHaveLength(6);

    await page.locator("input[placeholder='123456']").fill(otp);
    await page.locator("button:has-text('Confirm & Proceed')").click();

    await expect(page.locator("text=Two-Factor Email Ownership Confirmed")).toBeVisible({ timeout: 10000 });
    const btn2 = page.locator("button:has-text('Save Draft & Proceed to Documents')");
    await btn2.scrollIntoViewIfNeeded();
    await btn2.click({ force: true });

    // Step 3: Upload Compliance Documents
    await expect(page.locator("text=Upload Regulatory & Safety Documents")).toBeVisible({ timeout: 15000 });

    const fileInputs = page.locator("input[type='file']");
    await fileInputs.nth(0).setInputFiles("/tmp/sample_license.pdf");
    await page.waitForTimeout(1000);

    await fileInputs.nth(1).setInputFiles("/tmp/sample_fire_noc.pdf");
    await page.waitForTimeout(1000);

    const btn3 = page.locator("button:has-text('Review Application Summary')");
    await btn3.scrollIntoViewIfNeeded();
    await btn3.click({ force: true });

    // Step 4: Final Submission
    await expect(page.locator("text=Application Summary Review")).toBeVisible({ timeout: 10000 });
    const btn4 = page.locator("button:has-text('Final Submit Application')");
    await btn4.scrollIntoViewIfNeeded();
    await btn4.click({ force: true });

    await expect(page.locator("text=Application Submitted for District Verification")).toBeVisible({ timeout: 15000 });

    const appNumElement = page.locator("p.text-base.font-bold.text-blue-400");
    APP_NUMBER = (await appNumElement.innerText()).trim();
    expect(APP_NUMBER).toMatch(/^APP-/);

    const tokenElement = page.locator("p.text-xs.text-emerald-400");
    TRACKING_TOKEN = (await tokenElement.innerText()).trim();
    expect(TRACKING_TOKEN.length).toBeGreaterThan(16);
  });

  test("2. Public Application Tracking Workflow", async ({ page }) => {
    expect(APP_NUMBER).not.toBe("");
    expect(TRACKING_TOKEN).not.toBe("");

    await page.goto("/application/track");
    await expect(page.locator("text=Track Application Verification Status")).toBeVisible({ timeout: 15000 });

    await page.locator("input[placeholder*='APP-HOSP']").fill(APP_NUMBER);
    await page.locator("input[placeholder*='16+ character']").fill(TRACKING_TOKEN);
    await page.locator("button:has-text('Track Status')").click();

    await expect(page.locator("text=AIIMS Amritsar Annex Super Specialty").first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=DISTRICT REVIEW").first()).toBeVisible();

    const content = await page.content();
    expect(content).not.toContain("password_hash");
    expect(content).not.toContain("raw_token");
  });

  test("3. Reviewer Login & Operations Dashboard", async ({ page }) => {
    await signIn(page, "amritsar_district_admin", "district123");

    await expect(page.locator("text=Amritsar District Health Administration")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("button:has-text('Registration & Review')")).toBeVisible();
  });

  test("4 & 5. Reviewer Inbox & Dossier Inspection", async ({ page }) => {
    await signIn(page, "amritsar_district_admin", "district123");
    await page.goto("/reviewer");
    await expect(page.locator("text=Healthcare Registration Review Queue")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Awaiting My Action")).toBeVisible();

    await openDossier(page, APP_NUMBER);

    await expect(page.locator("text=AIIMS Amritsar Annex Super Specialty")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Operational Profile & Capacities")).toBeVisible();
    await expect(page.locator("text=Total Beds:")).toBeVisible();

    await page.locator("button:has-text('← Back to Application Queue')").click();
    await expect(page.locator("text=Healthcare Registration Review Queue")).toBeVisible();
  });

  test("6. Document Preview & Verification", async ({ page }) => {
    await signIn(page, "amritsar_district_admin", "district123");
    await page.goto("/reviewer");
    await openDossier(page, APP_NUMBER);

    // Inspect document preview modal
    const inspectBtn = page.locator("button:has-text('🔍 Inspect File')").first();
    await expect(inspectBtn).toBeVisible({ timeout: 10000 });
    await inspectBtn.click();

    await expect(page.locator("text=Download File")).toBeVisible();
    // Close modal using exact close button inside the modal dialog
    await page.locator(".fixed.inset-0").locator("button", { hasText: /^✕$/ }).click({ force: true });

    // Verify all pending documents
    while ((await page.locator("button:has-text('✓ Mark Verified'):not([disabled])").count()) > 0) {
      const vbtn = page.locator("button:has-text('✓ Mark Verified'):not([disabled])").first();
      await vbtn.scrollIntoViewIfNeeded();
      await vbtn.click({ force: true });
      await page.waitForTimeout(1000);
    }

    await expect(page.locator("text=Document checklist complete")).toBeVisible({ timeout: 10000 });
  });

  test("7. Hierarchical Decision: District -> State -> Central", async ({ page }) => {
    // Step A: District Reviewer forwards to State
    await signIn(page, "amritsar_district_admin", "district123");
    await page.goto("/reviewer");
    await openDossier(page, APP_NUMBER);

    const fwdBtn1 = page.locator("button:has-text('Forward to Next Review Authority →')");
    await fwdBtn1.scrollIntoViewIfNeeded();
    await fwdBtn1.click({ force: true });
    await expect(page.locator("text=Forward Application to Next Review Level")).toBeVisible();
    await page.locator("textarea[placeholder*='All clinical licenses']").fill("District CMO verified local infrastructure. Forwarding to State Director.");
    await page.locator("button:has-text('Confirm Forward →')").click({ force: true });

    await page.waitForTimeout(1500);

    // Step B: Log in as State Admin and Forward to Central
    await signOut(page);
    await signIn(page, "punjab_admin", "admin123");

    await page.goto("/reviewer");
    await openDossier(page, APP_NUMBER);

    const fwdBtn2 = page.locator("button:has-text('Forward to Next Review Authority →')");
    await fwdBtn2.scrollIntoViewIfNeeded();
    await fwdBtn2.click({ force: true });
    await expect(page.locator("text=Forward Application to Next Review Level")).toBeVisible();
    await page.locator("textarea[placeholder*='All clinical licenses']").fill("State healthcare board endorsed.");
    await page.locator("button:has-text('Confirm Forward →')").click({ force: true });

    await page.waitForTimeout(1500);

    // Step C: Log in as Central Admin and Approve
    await signOut(page);
    await signIn(page, "central_admin", "central123");

    await page.goto("/reviewer");
    await openDossier(page, APP_NUMBER);

    const apprvBtn = page.locator("button:has-text('✓ Final Approve & Provision Account')");
    await apprvBtn.scrollIntoViewIfNeeded();
    await apprvBtn.click({ force: true });
    await expect(page.locator("text=Final Central Approval & Account Provisioning")).toBeVisible();
    await page.locator("textarea[placeholder*='Cleared under National Referral']").fill("National accreditation granted.");
    await page.locator("button:has-text('Final Approve & Provision ✓')").click({ force: true });

    await expect(page.locator("text=Status: APPROVED")).toBeVisible({ timeout: 15000 });
  });

  test("8 & 9. Account Activation & Login after Activation", async ({ page }) => {
    const rawActivationToken = runHelper("get-activation-token", TEST_EMAIL);
    expect(rawActivationToken.length).toBeGreaterThan(20);

    await page.goto(`/activate?token=${rawActivationToken}`);
    await expect(page.locator("text=Activate Operational Account")).toBeVisible();

    const passInputs = page.locator("input[type='password']");
    await passInputs.nth(0).fill("SuperGovPass!2026");
    await passInputs.nth(1).fill("SuperGovPass!2026");

    const actBtn = page.locator("button:has-text('Confirm & Activate Account →')");
    await actBtn.scrollIntoViewIfNeeded();
    await actBtn.click({ force: true });

    await expect(page.locator("text=Account Activated Successfully")).toBeVisible({ timeout: 15000 });
    const usernameElement = page.locator("p.text-sm.font-bold.text-blue-400");
    PROVISIONED_USERNAME = (await usernameElement.innerText()).trim();
    expect(PROVISIONED_USERNAME).toMatch(/^gh\d+$/i);

    const goSignIn = page.locator("a:has-text('Sign In to Healthcare Dashboard →')");
    await goSignIn.scrollIntoViewIfNeeded();
    await goSignIn.click({ force: true });
    await expect(page).toHaveURL(/\/portal\/hospital\/login/);

    await page.locator("input[type='text']").fill(PROVISIONED_USERNAME);
    await page.locator("input[type='password']").fill("SuperGovPass!2026");
    const dashIn = page.locator("button[type='submit']");
    await dashIn.scrollIntoViewIfNeeded();
    await dashIn.click({ force: true });

    await expect(page.locator("text=AIIMS Amritsar Annex Super Specialty").first()).toBeVisible({ timeout: 15000 });
  });

  test("10. Forgot Password & Password Reset Workflow", async ({ page }) => {
    await signOut(page);
    await page.goto("/forgot-password");
    await expect(page.locator("text=Reset Account Password")).toBeVisible();

    await page.locator("input[type='email']").fill(TEST_EMAIL);
    const recBtn = page.locator("button:has-text('Send Recovery Instructions →')");
    await recBtn.scrollIntoViewIfNeeded();
    await recBtn.click({ force: true });

    await expect(page.locator("text=Password Recovery Request Received")).toBeVisible();
    await expect(page.locator(`text=${TEST_EMAIL}`)).toBeVisible();

    const resetToken = runHelper("get-reset-token", TEST_EMAIL);
    expect(resetToken.length).toBeGreaterThan(20);

    await page.goto(`/reset-password?token=${resetToken}`);
    await expect(page.locator("text=Set New Account Password")).toBeVisible();

    const passInputs = page.locator("input[type='password']");
    await passInputs.nth(0).fill("BrandNewPassword!2026");
    await passInputs.nth(1).fill("BrandNewPassword!2026");
    const updBtn = page.locator("button:has-text('Confirm & Update Password →')");
    await updBtn.scrollIntoViewIfNeeded();
    await updBtn.click({ force: true });

    await expect(page.locator("text=Password Successfully Updated")).toBeVisible({ timeout: 15000 });

    const newSign = page.locator("a:has-text('Sign In with New Password →')");
    await newSign.scrollIntoViewIfNeeded();
    await newSign.click({ force: true });
    await expect(page).toHaveURL(/\/portal\/hospital\/login/);

    await page.locator("input[type='text']").fill(PROVISIONED_USERNAME);
    await page.locator("input[type='password']").fill("BrandNewPassword!2026");
    const dashSign = page.locator("button[type='submit']");
    await dashSign.scrollIntoViewIfNeeded();
    await dashSign.click({ force: true });

    await expect(page.locator("text=AIIMS Amritsar Annex Super Specialty").first()).toBeVisible({ timeout: 15000 });
  });

  test("11. Rejection Workflow", async ({ page }) => {
    const rejEmail = `nodal_rej_${Date.now()}@gov.in`;
    await page.goto("/register/hospital");
    await page.locator("input[placeholder*='Guru Nanak Dev']").fill("Defunct Clinic Ludhiana");
    await page.locator("select").nth(0).selectOption("Punjab");
    await page.locator("select").nth(1).selectOption("Ludhiana");
    await page.locator("input[placeholder*='Amritsar']").fill("Ludhiana");
    const bedInputs = page.locator("input[type='number']");
    await bedInputs.nth(0).fill("40");
    await bedInputs.nth(1).fill("5");

    const rbtn1 = page.locator("button:has-text('Proceed to Contact & Verification')");
    await rbtn1.scrollIntoViewIfNeeded();
    await rbtn1.click({ force: true });

    await page.locator("input[placeholder*='Dr. Harpreet Singh']").fill("Dr. Non Compliant");
    await page.locator("input[placeholder*='Chief Medical Superintendent']").fill("Clinic Incharge");
    await page.locator("input[placeholder*='nodal.hospital']").fill(rejEmail);
    await page.locator("input[placeholder*='98765 43210']").fill("9876543211");
    await page.locator("button:has-text('Verify Email')").click();

    await page.waitForTimeout(800);
    const otp = runHelper("get-otp", rejEmail);
    await page.locator("input[placeholder='123456']").fill(otp);
    await page.locator("button:has-text('Confirm & Proceed')").click();

    await expect(page.locator("text=Two-Factor Email Ownership Confirmed")).toBeVisible({ timeout: 10000 });
    const rbtn2 = page.locator("button:has-text('Save Draft & Proceed to Documents')");
    await rbtn2.scrollIntoViewIfNeeded();
    await rbtn2.click({ force: true });

    await expect(page.locator("text=Upload Regulatory & Safety Documents")).toBeVisible({ timeout: 10000 });
    const fileInputs = page.locator("input[type='file']");
    await fileInputs.nth(0).setInputFiles("/tmp/sample_license.pdf");
    await fileInputs.nth(1).setInputFiles("/tmp/sample_fire_noc.pdf");
    const rbtn3 = page.locator("button:has-text('Review Application Summary')");
    await rbtn3.scrollIntoViewIfNeeded();
    await rbtn3.click({ force: true });
    const rbtn4 = page.locator("button:has-text('Final Submit Application')");
    await rbtn4.scrollIntoViewIfNeeded();
    await rbtn4.click({ force: true });
    await expect(page.locator("text=Application Submitted for District Verification")).toBeVisible({ timeout: 10000 });

    const rejAppNum = (await page.locator("p.text-base.font-bold.text-blue-400").innerText()).trim();

    await signOut(page);
    await signIn(page, "ludhiana_district_admin", "district123");

    await page.goto("/reviewer");
    await openDossier(page, rejAppNum);

    const rejBtn = page.locator("button:has-text('✕ Reject Application')");
    await rejBtn.scrollIntoViewIfNeeded();
    await rejBtn.click({ force: true });
    await expect(page.locator("text=Mandatory Rejection Reason *")).toBeVisible();
    await page.locator("textarea[placeholder*='Provide a detailed']").fill("Building fails basic fire egress corridor specifications.");
    await page.locator("button:has-text('Confirm Rejection ✕')").click({ force: true });

    await expect(page.locator("text=Status: REJECTED").first()).toBeVisible({ timeout: 15000 });
  });

  test("12. Unauthorized Role & Cross-Jurisdiction Boundary Enforcement", async ({ page }) => {
    // A. Operational Hospital User cannot access Reviewer Portal
    await signOut(page);
    await signIn(page, "gh00046", "hospital123");
    await expect(page.locator("text=Regional Amritsar Medical College Hospital")).toBeVisible({ timeout: 15000 });

    // Attempt direct navigation to /reviewer
    await page.goto("/reviewer");
    await expect(page.locator("text=Reviewer Authentication Required")).toBeVisible();

    // B. Cross-Jurisdiction: Ludhiana Admin attempting to view Amritsar Application
    await signOut(page);
    await signIn(page, "ludhiana_district_admin", "district123");

    // Attempt direct access to Amritsar application dossier
    await page.goto(`/reviewer/applications/${APP_NUMBER}`);
    await expect(
      page.locator("text=outside your district jurisdiction")
        .or(page.locator("text=Access denied"))
        .or(page.locator("text=Failed to load application dossier"))
        .or(page.locator("text=Forbidden"))
    ).toBeVisible({ timeout: 10000 });
  });
});
