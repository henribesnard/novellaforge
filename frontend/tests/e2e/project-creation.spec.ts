import { test, expect } from '@playwright/test';

test.describe('Project Creation Wizard', () => {
    test('should allow creating a project with custom genre, size, and lazy mode', async ({ page }) => {
        // Mock API calls to decouple from the backend
        await page.route('**/api/v1/projects/concept/proposal*', async route => {
            await route.fulfill({
                json: {
                    concept: {
                        title: 'Chroniques de la cité perdue',
                        premise: 'Une mission de sauvetage tourne mal...',
                        tone: 'Dark, tense',
                        tropes: ['Cyberpunk', 'Mystery'],
                        emotional_orientation: 'Suspense'
                    }
                }
            });
        });

        await page.route('**/api/v1/projects/', async route => {
            await route.fulfill({
                json: {
                    id: 'test-project-123',
                    title: 'Chroniques de la cité perdue',
                    status: 'draft'
                }
            });
        });

        await page.route('**/api/v1/projects/*/concept', async route => {
            await route.fulfill({ json: { success: true } });
        });

        // Inject auth token to bypass login redirect
        await page.addInitScript(() => {
            window.localStorage.setItem('auth_token', 'mock-token-for-e2e-tests');
        });

        // We navigate directly to the dashboard with the create parameter to trigger the modal.
        // Assuming local dev bypasses auth or handles it via mock/default token if needed.
        await page.goto('/dashboard?create=1');

        // Wait for the dialog to appear
        const dialogTitle = page.getByText('Creer un nouveau projet', { exact: true });
        await expect(dialogTitle).toBeVisible({ timeout: 10000 });

        // Step 1: Genre selection
        const genreInput = page.getByPlaceholder('Ex: Fantasy, Cyberpunk...');
        await genreInput.fill('Science-Fiction Cyberpunk');

        // The component for "Nombre de chapitres cible" (second input of type number)
        const chapterCountInput = page.getByPlaceholder('Ex: 30');
        await chapterCountInput.fill('10');

        // Proceed to generate concept
        const generateBtn = page.getByRole('button', { name: /Generer une proposition/i });
        await generateBtn.click();

        // The UI should show "Titre propose" and other fields once generation is successful
        const titleInput = page.getByPlaceholder(/Titre de projet/i);
        await expect(titleInput).toBeVisible({ timeout: 10000 });

        // Verify it proposed something
        const proposedTitle = await titleInput.inputValue();
        expect(proposedTitle?.length).toBeGreaterThan(0);

        // Validate and create
        const createProjectBtn = page.getByRole('button', { name: /Creer le projet/i });
        await createProjectBtn.click();

        // After creation, it should navigate or close the dialog
        await expect(dialogTitle).not.toBeVisible({ timeout: 10000 });
    });
});
