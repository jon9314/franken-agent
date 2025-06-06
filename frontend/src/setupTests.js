import { expect, afterEach, vi } from 'vitest'; // vi for mocking if needed
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom'; // Extends `expect` with jest-dom matchers like .toBeInTheDocument()

// Mock global window.confirm for tests that might use it, to prevent test runner hangs
// You can make it more sophisticated by checking arguments or returning different values
global.confirm = vi.fn(() => true); // Default to true (user clicks "OK")
// To test different scenarios:
// beforeEach(() => {
//   vi.mocked(global.confirm).mockClear().mockReturnValue(true); 
// });
// In a test: vi.mocked(global.confirm).mockReturnValueOnce(false);

// Runs a cleanup function (e.g., unmounting components) after each test case.
// This is good practice to ensure tests are isolated.
afterEach(() => {
  cleanup();
});