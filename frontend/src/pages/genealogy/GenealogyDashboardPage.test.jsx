import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import GenealogyDashboardPage from './GenealogyDashboardPage'; // The component to test
import apiClient from '@/api/index.js'; // The API client we need to mock

// Mock the apiClient to prevent actual network calls during tests.
// All calls to `apiClient.get` will now be handled by our mock.
vi.mock('@/api/index.js', () => ({
  default: {
    get: vi.fn(), // Mock the .get method
    post: vi.fn(), // Also mock .post for uploads
  },
}));

// A wrapper component to provide necessary context (like BrowserRouter) for our tests
const renderWithRouter = (ui, { route = '/' } = {}) => {
  window.history.pushState({}, 'Test page', route);
  return render(ui, { wrapper: BrowserRouter });
};

describe('GenealogyDashboardPage', () => {

  // Reset mocks before each test to ensure test isolation
  beforeEach(() => {
    vi.mocked(apiClient.get).mockClear();
    vi.mocked(apiClient.post).mockClear();
  });

  it('renders the main heading and upload component when loading', () => {
    // Arrange: Mock a pending API response
    apiClient.get.mockResolvedValue({ data: [] });
    
    // Act
    renderWithRouter(<GenealogyDashboardPage />);

    // Assert
    // Check if the main title is on the page
    expect(screen.getByRole('heading', { name: /Genealogy Dashboard/i })).toBeInTheDocument();

    // Check if the upload section title is present
    expect(screen.getByRole('heading', { name: /Upload New Family Tree/i })).toBeInTheDocument();
  });

  it('displays the list of family trees after a successful API call', async () => {
    // Arrange: Mock a successful API response with some tree data
    const mockTrees = [
      { id: 1, file_name: 'smith_family.ged', owner_id: 1, created_at: new Date().toISOString() },
      { id: 2, file_name: 'jones_family.ged', owner_id: 1, created_at: new Date().toISOString() },
    ];
    apiClient.get.mockResolvedValue({ data: mockTrees });

    // Act
    renderWithRouter(<GenealogyDashboardPage />);

    // Assert
    // Wait for the "Loading..." message to disappear
    await waitFor(() => {
      expect(screen.queryByText(/Loading your family trees.../i)).not.toBeInTheDocument();
    });

    // Check if the tree names are rendered on the page
    expect(screen.getByText('smith_family.ged')).toBeInTheDocument();
    expect(screen.getByText('jones_family.ged')).toBeInTheDocument();
  });

  it('displays an empty state message when no trees are available', async () => {
    // Arrange: Mock a successful API response with an empty array
    apiClient.get.mockResolvedValue({ data: [] });

    // Act
    renderWithRouter(<GenealogyDashboardPage />);

    // Assert
    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByText(/Loading your family trees.../i)).not.toBeInTheDocument();
    });

    // Check that the "No family trees" message is displayed
    expect(screen.getByText(/No family trees have been uploaded yet./i)).toBeInTheDocument();
  });

  it('displays an error message if the API call to fetch trees fails', async () => {
    // Arrange: Mock a rejected API call
    apiClient.get.mockRejectedValue(new Error('Network Error'));

    // Act
    renderWithRouter(<GenealogyDashboardPage />);

    // Assert
    // Wait for the error message to appear
    const errorMessage = await screen.findByText(/Failed to load your family trees./i);
    expect(errorMessage).toBeInTheDocument();
  });

});