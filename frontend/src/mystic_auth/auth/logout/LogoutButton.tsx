import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useLogoutMutation } from "./useLogoutMutation";
import LogoutButtonComponent from "./LogoutButtonComponent";

const LogoutButton: React.FC = () => {
    const logoutMutation = useLogoutMutation();
    const navigate = useNavigate();

    const handleLogout = () => {
        logoutMutation.mutate();
    };

    useEffect(() => {
        if (logoutMutation.isSuccess) {
            navigate("/login");
        }
    }, [logoutMutation.isSuccess, navigate]);

    return (
        <LogoutButtonComponent
            loading={logoutMutation.isPending}
            error={logoutMutation.error?.message ?? null}
            successMessage={logoutMutation.data?.message ?? null}
            onLogout={handleLogout}
        />
    );
};

export default LogoutButton;
