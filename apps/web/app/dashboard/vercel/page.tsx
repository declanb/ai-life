import VercelDashboard from "@/components/vercel/VercelDashboard";

export default function VercelPage() {
  return (
    <div className="flex flex-col gap-4 px-4 py-4 md:gap-6 md:py-6 lg:px-6">
      <VercelDashboard />
    </div>
  );
}
