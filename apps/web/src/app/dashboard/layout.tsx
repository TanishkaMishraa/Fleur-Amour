import { Sidebar } from "@/components/layout/Sidebar";
import { DashboardTopbar } from "@/components/layout/DashboardTopbar";
import { RouteGuard } from "@/components/shared/RouteGuard";

export const metadata = { title: "Dashboard" };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          <DashboardTopbar />
          <main className="flex-1 overflow-y-auto hide-scrollbar">
            <div className="h-full p-6 md:p-8 max-w-screen-2xl mx-auto">
              {children}
            </div>
          </main>
        </div>
      </div>
    </RouteGuard>
  );
}
