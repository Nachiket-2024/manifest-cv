import React from "react";
import { Box, Stack, Text } from "@chakra-ui/react";
import { NavLink } from "react-router-dom";

import { IfCan } from "../authorization/IfCan";
import { NAV_ITEMS } from "./navItems";
import { APP_NAME } from "../core/settings";

interface SidebarProps {
    isOpen: boolean;
    onNavigate: () => void;
}

/**
 * Primary app navigation. Permanently visible on md+ screens; on smaller
 * screens it's an off-canvas panel toggled by Navbar's menu button (slides
 * in via transform so it stays in the DOM — avoids remounting nav state).
 * Each permission-gated link is wrapped in IfCan so a caller who lacks that
 * permission never sees it; the route itself is still independently
 * enforced by ProtectedRoute.
 */
const Sidebar: React.FC<SidebarProps> = ({ isOpen, onNavigate }) => {
    return (
        <Box
            as="nav"
            aria-label="Main navigation"
            position={{ base: "fixed", md: "sticky" }}
            top={0}
            left={0}
            h="100vh"
            w="240px"
            flexShrink={0}
            bg="bg.surface"
            borderRight="1px solid"
            borderColor="border.default"
            zIndex="overlay"
            transform={{ base: isOpen ? "translateX(0)" : "translateX(-100%)", md: "none" }}
            transition="transform 0.2s ease"
            display="flex"
            flexDirection="column"
        >
            <Box px={6} py={5} borderBottom="1px solid" borderColor="border.default">
                <Text fontWeight="bold" fontSize="lg" color="brand.fg">
                    {APP_NAME}
                </Text>
            </Box>

            <Stack p={3} gap={1}>
                {NAV_ITEMS.map((item) => {
                    const link = (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            onClick={onNavigate}
                            style={({ isActive }) => ({
                                display: "block",
                                padding: "8px 12px",
                                borderRadius: "6px",
                                fontWeight: isActive ? 600 : 500,
                                color: isActive ? "var(--chakra-colors-brand-fg)" : "var(--chakra-colors-fg-default)",
                                background: isActive ? "var(--chakra-colors-brand-muted)" : "transparent",
                            })}
                        >
                            {item.label}
                        </NavLink>
                    );

                    if (!item.permission) return link;

                    return (
                        <IfCan key={item.to} action={item.permission}>
                            {link}
                        </IfCan>
                    );
                })}
            </Stack>
        </Box>
    );
};

export default Sidebar;
