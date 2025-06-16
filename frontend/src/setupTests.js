import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom'; // Extends `expect` with jest-dom matchers

// Mock global window.confirm for tests that might use it, to prevent the test runner from hanging
// By default, it will simulate the user clicking "OK".
global.confirm = vi.fn(() => true); 

// To test a specific scenario where the user clicks "Cancel", you can mock it in a test:
// beforeEach(() => {
//   vi.mocked(global.confirm).mockClear().mockReturnValue(true); 
// });
// In a specific test: vi.mocked(global.confirm).mockReturnValueOnce(false);

// This is a standard cleanup routine from react-testing-library.
// It runs after each test case and unmounts any rendered React components,
// ensuring that tests are isolated from each other.
afterEach(() => {
  cleanup();
});