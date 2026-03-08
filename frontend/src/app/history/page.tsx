import AppHeader from "../../components/AppHeader";
import BottomNav from "../../components/BottomNav";

const historyItems = [
  {
    id: 1,
    title: "Hospital visit",
    summary: "Doctor asked about symptoms and medication.",
    time: "Today, 10:12 AM",
  },
  {
    id: 2,
    title: "Transit help",
    summary: "Asked for the correct platform and next arrival.",
    time: "Yesterday, 5:48 PM",
  },
  {
    id: 3,
    title: "Coffee shop order",
    summary: "Used quick replies to order a drink.",
    time: "Yesterday, 2:15 PM",
  },
];

export default function HistoryPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 pb-24">
      <AppHeader />

      <section className="mx-auto max-w-md px-4 py-6">
        <div className="mb-5">
          <p className="text-sm font-semibold text-gray-500">History</p>
          <h1 className="text-2xl font-bold text-gray-900">Past conversations</h1>
        </div>

        <div className="flex flex-col gap-4">
          {historyItems.map((item) => (
            <div
              key={item.id}
              className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm"
            >
              <h2 className="text-lg font-bold text-gray-900">{item.title}</h2>
              <p className="mt-2 text-sm text-gray-600">{item.summary}</p>
              <p className="mt-3 text-xs font-medium text-gray-400">{item.time}</p>
            </div>
          ))}
        </div>
      </section>

      <BottomNav />
    </main>
  );
}