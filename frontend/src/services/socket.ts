import { io } from "socket.io-client";

export const socket = io(process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://localhost:8080", {
  autoConnect: false,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  timeout: 10000,
});
