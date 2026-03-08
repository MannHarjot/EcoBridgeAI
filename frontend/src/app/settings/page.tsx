import AppHeader from "../../components/AppHeader";
import BottomNav from "../../components/BottomNav";

const settings = [
  "Large text mode",
  "High contrast mode",
  "Vibration on new transcript",
  "Auto speak selected replies",
  "Save custom phrases",
];

export default function SettingsPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 pb-24">
      <AppHeader />

      <section className="mx-auto max-w-md px-4 py-6">
        <div className="mb-5">
          <p className="text-sm font-semibold text-gray-500">Settings</p>
          <h1 className="text-2xl font-bold text-gray-900">Accessibility preferences</h1>
        </div>

        <div className="flex flex-col gap-4">
          {settings.map((item) => (
            <div
              key={item}
              className="flex items-center justify-between rounded-3xl border border-gray-200 bg-white p-5 shadow-sm"
            >
              <span className="text-base font-medium text-gray-800">{item}</span>
              <div className="h-6 w-11 rounded-full bg-gray-200 p-1">
                <div className="h-4 w-4 rounded-full bg-white shadow-sm" />
              </div>
            </div>
          ))}
        </div>
      </section>

      <BottomNav />
    </main>
  );
}