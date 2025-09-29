import { create } from "zustand";
import { persist } from "zustand/middleware";
import { listTennants } from "../lib/apiClient";
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

      return {
        tennants: null,
        loadTennants,
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
