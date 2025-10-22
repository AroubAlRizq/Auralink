// src/lib/storage.js
import { createClient } from "@supabase/supabase-js";

const url = (import.meta.env?.VITE_SUPABASE_URL || "").trim();
const anon = (import.meta.env?.VITE_SUPABASE_ANON_KEY || "").trim();

let supabase = null;
if (url && anon) {
  try {
    supabase = createClient(url, anon);
  } catch (e) {
    console.warn("Supabase client init failed:", e);
    supabase = null;
  }
} else {
  console.warn("Supabase disabled: missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY");
}

/**
 * Uploads a file to Supabase Storage and returns its public URL.
 * If Supabase isn't configured, this will throw an Error at CALL time (not import time).
 */
export async function uploadVideoAndGetPublicUrl(file, meetingId, bucket = "videos") {
  if (!supabase) {
    throw new Error("Storage not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.");
  }

  const ext = file.name.split(".").pop()?.toLowerCase() || "mp4";
  const path = `${meetingId}/${Date.now()}.${ext}`;

  // If you did not add an UPDATE policy, keep upsert:false
  const { error: upErr } = await supabase
    .storage
    .from(bucket)
    .upload(path, file, { upsert: false, contentType: file.type || "video/mp4" });

  if (upErr) {
    console.error("Supabase upload error:", upErr);
    throw new Error(upErr.message || "Upload failed (check Storage policies & bucket name).");
  }

  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  if (!data?.publicUrl) throw new Error("Could not get public URL from Supabase.");
  return data.publicUrl;
}