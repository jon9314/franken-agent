import { Routes, Route, Navigate } from 'react-router-dom';

// Layout Components
import Header from '@/components/layout/Header';
import RequireAuth from '@/components/layout/RequireAuth';

// Core Pages
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Chat from '@/pages/Chat';

// Admin Section Pages/Components
import Admin from '@/pages/Admin'; // Admin Layout Page
import UserManagementPanel from '@/components/admin/UserManagementPanel';
import AgentDashboard from '@/components/admin/agent/AgentDashboard';
import AgentTaskReview from '@/components/admin/agent/AgentTaskReview';
import AgentPermissionsPanel from '@/components/admin/agent/AgentPermissionsPanel';
import NotificationSettingsPanel from '@/components/admin/settings/NotificationSettingsPanel';
import GenealogyFindingsReviewPage from '@/components/admin/genealogy/GenealogyFindingsReviewPage';

// Genealogy User-Facing Pages
import GenealogyDashboardPage from '@/pages/genealogy/GenealogyDashboardPage';
import FamilyTreeDetailPage from '@/pages/genealogy/FamilyTreeDetailPage';

// Fallback/Error Page (Optional)
// import NotFoundPage from '@/pages/NotFoundPage';

function App() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex flex-col">
      <Header />
      <main className="flex-grow container mx-auto py-6 px-4 sm:px-6 lg:px-8 w-full">
        <Routes>
          {/* --- Public Routes --- */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* --- Protected Routes (for 'user' and 'admin') --- */}
          <Route element={<RequireAuth allowedRoles={['user', 'admin']} />}>
            <Route path="/" element={<Chat />} />
            <Route path="/chat" element={<Navigate to="/" replace />} /> {/* Alias for chat */}
            
            {/* Genealogy User-Facing Routes */}
            <Route path="/genealogy" element={<GenealogyDashboardPage />} />
            <Route path="/genealogy/trees/:treeId" element={<FamilyTreeDetailPage />} />
            {/* Note: Reviewing specific person's findings might be linked from FamilyTreeDetailPage to an admin route if desired */}
          </Route>
          
          {/* --- Admin Protected Routes --- */}
          <Route element={<RequireAuth allowedRoles={['admin']} />}>
            <Route path="/admin" element={<Admin />}> {/* Admin serves as a layout for its sub-routes */}
              {/* Default child route for /admin, e.g., redirect to user management */}
              <Route index element={<Navigate to="users" replace />} /> 
              <Route path="users" element={<UserManagementPanel />} />
              <Route path="agent" element={<AgentDashboard />} />
              <Route path="agent/task/:taskId" element={<AgentTaskReview />} />
              <Route path="permissions" element={<AgentPermissionsPanel />} />
              <Route path="settings" element={<NotificationSettingsPanel />} />
              <Route path="genealogy-review" element={<GenealogyFindingsReviewPage />} />
              {/* Add more admin sub-routes here as needed */}
            </Route>
          </Route>

          {/* --- Fallback for any unknown routes --- */}
          {/* Option 1: Redirect to home (if user is auth'd) or login */}
          <Route path="*" element={<Navigate to="/" replace />} />
          {/* Option 2: Show a dedicated 404 Not Found page */}
          {/* <Route path="*" element={<NotFoundPage />} /> */}
        </Routes>
      </main>
      {/* Optional Global Footer can go here */}
      {/* <footer className="bg-white border-t border-gray-200 text-center p-4 text-sm text-gray-500">
        Frankie AI Web Agent &copy; {new Date().getFullYear()}
      </footer> */}
    </div>
  );
}

export default App;