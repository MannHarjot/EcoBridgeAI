"use client";

import { Status } from "../types";

interface Props {
  status: Status;
}

export default function StatusBar({ status }: Props) {
  const styles: Record<Status, string> = {
    idle: "bg-gray-100 text-gray-700",
    listening: "bg-blue-100 text-blue-700",
    processing: "bg-yellow-100 text-yellow-700",
    speaking: "bg-green-100 text-green-700",
    offline: "bg-red-100 text-red-700",
  };

  return (
    <div className="mx-auto w-full max-w-md px-4">
      <div className={`mt-4 rounded-2xl px-4 py-3 text-sm font-medium ${styles[status]}`}>
        Status: {status}
      </div>
    </div>
  );
}