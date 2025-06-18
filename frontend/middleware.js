import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware();

export const config = {
  matcher: [
    // tutte le route che vuoi proteggere con getAuth
    "/upload-audio",
    "/transcription-editor",
    "/summary-editor",
    "/dashboard",
    "/admin-dashboard", // nuova rotta protetta
  ],
};