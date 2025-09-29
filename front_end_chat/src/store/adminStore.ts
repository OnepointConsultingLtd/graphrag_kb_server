import { create } from "zustand";
import { persist } from "zustand/middleware";
import { listTennants, createTenant as createTenantApi, deleteTenant as deleteTenantApi } from "../lib/apiClient";
import type { AdminStore } from "../type/adminStore";

const useAdminStore = create<AdminStore>()(
  persist(
    (set) => {
      async function loadTennants(jwt: string) {
        try {
          const tennants = await listTennants(jwt);
          console.log("tennants", tennants)
          set({ tennants });
        } catch (error) {
          console.error("Failed to load tennants:", error);
          set({ tennants: null });
        }
      }

      async function createTenant(jwt: string, tenantData: { tennant_name: string; email: string }) {
        try {
          await createTenantApi(jwt, tenantData);
          await loadTennants(jwt);
        } catch (error) {
          console.error("Failed to create tenant:", error);
          throw error;
        }
      }

      async function deleteTenant(jwt: string, tenantId: string) {
        try {
          await deleteTenantApi(jwt, tenantId);
          await loadTennants(jwt);
        } catch (error) {
          console.error("Failed to delete tenant:", error);
          throw error;
        }
      }

      return {
        tennants: null,
        loadTennants,
        createTenant,
        deleteTenant,
      };
    },
    {
      name: "admin-store",
      partialize: (state) => ({
        tennants: state.tennants,
      }),
    },
  ),
);

export default useAdminStore;
