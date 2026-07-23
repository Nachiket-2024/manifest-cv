import React, { useEffect, useState } from "react";
import { Box, Flex } from "@chakra-ui/react";

import Sidebar from "./Sidebar";
import Navbar from "./Navbar";

interface AppLayoutProps {
    children: React.ReactNode;
}

/**
 * Shared shell (sidebar + top bar) for every authenticated page. Wraps a
 * page's content the same way ProtectedRoute wraps its access check — a
 * page component itself stays focused on its own content, not layout
 * chrome.
 */
const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    // Escape closes the off-canvas nav, same as clicking the backdrop —
    // keyboard users shouldn't need a pointer to dismiss it.
    useEffect(() => {
        if (!mobileNavOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") setMobileNavOpen(false);
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [mobileNavOpen]);

    return (
        <Flex minH="100vh" bg="bg.canvas">
            <Sidebar isOpen={mobileNavOpen} onNavigate={() => setMobileNavOpen(false)} />

            {/* Backdrop for the off-canvas sidebar on small screens */}
            {mobileNavOpen && (
                <Box
                    position="fixed"
                    inset={0}
                    bg="blackAlpha.600"
                    zIndex="overlay"
                    display={{ base: "block", md: "none" }}
                    onClick={() => setMobileNavOpen(false)}
                    aria-hidden="true"
                />
            )}

            <Flex direction="column" flex="1" minW={0}>
                <Navbar onToggleSidebar={() => setMobileNavOpen((open) => !open)} />
                <Box as="main" flex="1" p={{ base: 4, md: 8 }} w="full">
                    {children}
                </Box>
            </Flex>
        </Flex>
    );
};

export default AppLayout;
