import { useLocation, Navigate, Outlet } from "react-router-dom";
import useAuth from "@/hooks/useAuth"; // Ensure path to useAuth hook is correct

const RequireAuth = ({ allowedRoles }) => {
    const { auth } = useAuth(); // auth object includes: token, user, isLoading
    const location = useLocation(); // Current location to redirect back after login

    // Handle the initial loading state from AuthProvider
    if (auth.isLoading) {
        // Render a loading indicator while authentication status is being determined
        return (
            <div className="flex items-center justify-center min-h-[calc(100vh-10rem)]">
                <div className="text-lg text-gray-600">Verifying authentication...</div>
                {/* You can replace this with a more sophisticated spinner component */}
            </div>
        );
    }

    const userIsAuthenticated = auth?.token && auth?.user;
    const userRole = auth?.user?.role;

    if (!userIsAuthenticated) {
        // User is not authenticated, redirect them to the /login page.
        // Save the current location they were trying to go to in the `state` property
        // so they can be redirected back to it after they successfully log in.
        // `replace` prop avoids adding the login route to the history stack.
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // If allowedRoles are specified, check if the user's role is among them.
    if (allowedRoles && allowedRoles.length > 0) {
        if (!userRole || !allowedRoles.includes(userRole)) {
            // User is authenticated but does not have the required role.
            // Redirect them to a "Not Authorized" page or simply to the home page.
            // For simplicity, redirecting to home.
            // You might want to create a dedicated /unauthorized page.
            console.warn(`RequireAuth: User role '${userRole}' not in allowed roles: ${allowedRoles.join(', ')} for path ${location.pathname}`);
            return <Navigate to="/" state={{ from: location, message: "You are not authorized to view this page." }} replace />;
        }
    }

    // If user is authenticated and (if roles specified) their role matches, render the child routes.
    return <Outlet />; 
    // Outlet is a placeholder where nested routes defined within this RequireAuth route will be rendered.
}

export default RequireAuth;