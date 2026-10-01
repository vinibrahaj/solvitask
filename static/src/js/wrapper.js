/** @odoo-module **/
import { registry } from "@web/core/registry";

const solvitaskTheme = {
    start() {
        const apply = () => {
            const brand = document.querySelector(".o_menu_brand");
            document.body.classList.toggle(
                "o_solvitask_theme",
                brand?.textContent.trim() === "SolviTask"
            );
        };
        apply();
        new MutationObserver(apply).observe(document.body, {
            childList: true,
            subtree: true,
        });
    },
};

registry.category("services").add("solvitask_theme", solvitaskTheme);
