import { test, expect } from '@playwright/test';

test.describe('Lazy Mode Reader', () => {
    test('should allow generating a new chapter iteratively', async ({ page }) => {
        // For the sake of the E2E test, we navigate directly to the reader mode
        // The URL structure expects a project ID: /projects/[id]/reader or similar.
        // Since we don't know an exact mock ID without running the backend, we mock the API.

        // Inject auth token to bypass login redirect
        await page.addInitScript(() => {
            window.localStorage.setItem('auth_token', 'mock-token-for-e2e-tests');
        });

        // Let's mock the /api/v1/writing/documents endpoint
        await page.route('**/api/v1/writing/documents*', async route => {
            const json: any[] = []; // No chapters yet
            await route.fulfill({ json });
        });

        // We can just visit a fake project ID directly if we mock everything
        await page.goto('/projects/test-project-123/reader');

        // The reader should show "L'histoire n'a pas encore commencé."
        await expect(page.locator('text=L\'histoire n\'a pas encore commencé.')).toBeVisible();

        // There should be a generic instruction input and a button to generate next
        const instructionInput = page.getByPlaceholder(/Le héros découvre un passage secret/i);
        await instructionInput.fill('Le protagoniste trouve un indice caché.');

        const generateBtn = page.getByRole('button', { name: /Générer la suite/i });
        await generateBtn.click();

        // Since we can't easily mock WebSockets natively in Playwright without some setup, 
        // the actual integration test against a local running backend will exercise the real WebSocket logic.
        // If this runs against a live backend, it will show "Écriture en cours..." and eventually chapter text.

        // When generating, the button is disabled and says "Générer la suite"
        const generateBtnLoading = page.getByRole('button', { name: /Générer la suite/i });
        await expect(generateBtnLoading).toBeDisabled({ timeout: 10000 });
    });
});
