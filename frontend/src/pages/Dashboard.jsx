import { useState, useRef } from "react";

export default function Dashboard() {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const inputRef = useRef(null);

  const onDrop = (e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); };
  const onBrowse = (e) => { const f = e.target.files?.[0]; if (f) setFile(f); };

  return (
    <div className="w-full">
      {/* Full-width hero directly under the header */}
      <div className="w-full">
        <img
          src="/hero-auralink.webp"     // put this image in /public
          alt="Auralink hero"
          className="w-full h-[320px] md:h-[400px] object-cover"
        />
      </div>

      {/* Uploader */}
      <div className="max-w-2xl mx-auto py-8 px-6">
        <div className="card">
          <h2 className="text-2xl font-semibold text-[#4C2E91] mb-2">Upload Meeting</h2>
          <p className="text-gray-600 mb-6">
            Upload your meeting video or audio to automatically extract summaries and insights.
          </p>

          <div
            onDragOver={(e)=>e.preventDefault()}
            onDrop={onDrop}
            className="rounded-lg border-2 border-dashed border-gray-300 py-16 text-center mb-4 hover:border-gray-400 transition cursor-pointer"
            onClick={()=>inputRef.current?.click()}
          >
            <div className="text-gray-700 font-medium">
              {file ? file.name : "Drag & Drop your file here"}
            </div>
          </div>

          <input ref={inputRef} type="file" className="hidden" onChange={onBrowse} />
          <input
            className="input focus-ring-teal mb-4"
            placeholder="Title (optional)"
            value={title}
            onChange={(e)=>setTitle(e.target.value)}
          />

          <button className="btn btn--primary w-full" disabled={!file}>
            Upload & Process
          </button>
        </div>
      </div>
    </div>
  );
}