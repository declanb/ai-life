import VercelDashboard from "../components/vercel/VercelDashboard";
import TransitDashboard from "../components/transit/TransitDashboard";
import TravelDashboard from "../components/travel/TravelDashboard";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#050510] text-white selection:bg-purple-500/30">
      <TravelDashboard />
      <VercelDashboard />
      <TransitDashboard />
    </main>
  );
}
