export default function Timeline() {
  return (
    <div className="max-w-6xl mx-auto py-10 px-6 space-y-8">
      <div className="card">
        <h2 className="text-2xl font-semibold text-[#4C2E91] mb-2">Conversation Timeline</h2>

        {/* Large space ready for backend-rendered content */}
        <div className="min-h-[360px] rounded-md border border-gray-200 bg-white p-4 text-gray-800 leading-relaxed">
          {/* Content from backend will be injected here */}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="font-semibold text-gray-700">Key Moments</div>
          <p className="text-sm text-gray-500">Auto-bookmarks.</p>
        </div>
        <div className="card">
          <div className="font-semibold text-gray-700">Speakers</div>
          <p className="text-sm text-gray-500">Speaker shares & turns.</p>
        </div>
        <div className="card">
          <div className="font-semibold text-gray-700">Filters</div>
          <p className="text-sm text-gray-500">Time / speaker / topic.</p>
        </div>
      </div>
    </div>
  );
}