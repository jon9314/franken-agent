import { useContext, useDebugValue } from "react";
import AuthContext from "@/context/AuthProvider"; // Ensure the path to AuthProvider is correct

const useAuth = () => {
    const context = useContext(AuthContext);

    // Throw an error if the hook is used outside of an AuthProvider
    // This is a good practice to catch common errors early.
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    // useDebugValue can be helpful for React DevTools to display a label for this custom Hook
    // It shows the logged-in status based on the presence of a user in the auth state.
    useDebugValue(context.auth, auth => auth?.user ? "Logged In" : "Logged Out");
    
    return context; // Return the full context value (which includes auth, setAuth, login, logout, register)
}

export default useAuth;