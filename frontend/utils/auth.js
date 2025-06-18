// lib/auth.js
import { getAuth } from "@clerk/nextjs/server";

/**
 * Protegge una pagina server-side.
 * Se l'utente è autenticato, chiama la funzione `callback(ctx, userId)`
 * Altrimenti esegue redirect verso la pagina di login.
 */
export const withAuthPage = (callback) => {
  return async (ctx) => {
    const { userId } = getAuth(ctx.req);

    if (!userId) {
      return {
        redirect: {
          destination: "/",
          permanent: false,
        },
      };
    }

    return callback(ctx, userId);
  };
};
