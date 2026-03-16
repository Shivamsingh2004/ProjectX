"use client";

import { useEffect } from "react";
import { socket } from "@/services/socket";

export function useRealtime() {
  useEffect(() => {
    socket.connect();
    return () => {
      socket.disconnect();
    };
  }, []);
}
