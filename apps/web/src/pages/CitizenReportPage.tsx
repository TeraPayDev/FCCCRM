import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { citizenApi } from "../api/client";
import "./citizen-report.css";

type Draft = {
  hazard_type: string;
  description: string;
  latitude?: number;
  longitude?: number;
  reporter_name?: string;
  reporter_contact?: string;
  consent_to_contact: boolean;
};

type QueuedReport = {
  id: string;
  draft: Draft;
  photo?: Blob;
  photoName?: string;
  photoType?: string;
  reportId?: string;
  createdAt: string;
};

const DB_NAME = "cram-citizen-reports";
const DB_VERSION = 1;
const STORE_NAME = "offline-reports";
const LEGACY_QUEUE_KEY = "cram.citizen.offline.queue.v1";

function createLocalId(): string {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `local-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;

      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getQueuedReports(): Promise<QueuedReport[]> {
  const db = await openDatabase();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.getAll();

    request.onsuccess = () => resolve(request.result as QueuedReport[]);
    request.onerror = () => reject(request.error);

    transaction.oncomplete = () => db.close();
  });
}

async function saveQueuedReport(item: QueuedReport): Promise<void> {
  const db = await openDatabase();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(item);

    transaction.oncomplete = () => {
      db.close();
      resolve();
    };

    transaction.onerror = () => {
      db.close();
      reject(transaction.error);
    };
  });
}

async function deleteQueuedReport(id: string): Promise<void> {
  const db = await openDatabase();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).delete(id);

    transaction.oncomplete = () => {
      db.close();
      resolve();
    };

    transaction.onerror = () => {
      db.close();
      reject(transaction.error);
    };
  });
}

async function migrateLegacyQueue(): Promise<void> {
  const raw = localStorage.getItem(LEGACY_QUEUE_KEY);
  if (!raw) return;

  try {
    const drafts = JSON.parse(raw) as Draft[];

    for (const draft of drafts) {
      await saveQueuedReport({
        id: createLocalId(),
        draft,
        createdAt: new Date().toISOString(),
      });
    }

    localStorage.removeItem(LEGACY_QUEUE_KEY);
  } catch {
    // Leave legacy data untouched if migration cannot be completed.
  }
}

function fileFromQueuedReport(item: QueuedReport): File | undefined {
  if (!item.photo) return undefined;

  return new File([item.photo], item.photoName ?? "attachment", {
    type: item.photoType ?? item.photo.type,
  });
}

export function CitizenReportPage() {
  const [hazard, setHazard] = useState("FLOOD");
  const [description, setDescription] = useState("");
  const [coords, setCoords] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [queued, setQueued] = useState(0);
  const [online, setOnline] = useState(navigator.onLine);
  const [syncing, setSyncing] = useState(false);

  const refreshQueueCount = useCallback(async () => {
    try {
      const pending = await getQueuedReports();
      setQueued(pending.length);
    } catch {
      setMessage("Unable to read reports saved on this device.");
    }
  }, []);

  const flushQueue = useCallback(async () => {
    if (!navigator.onLine) return;

    setSyncing(true);

    try {
      const pending = await getQueuedReports();

      for (const item of pending) {
        try {
          let reportId = item.reportId;

          if (!reportId) {
            const report = await citizenApi.submit(item.draft);
            reportId = String(report.id);

            // Persist the server report ID before attempting the photo.
            // If the photo upload fails, retrying will not create a
            // duplicate citizen report.
            await saveQueuedReport({
              ...item,
              reportId,
            });
          }

          const queuedPhoto = fileFromQueuedReport(item);

          if (queuedPhoto) {
            await citizenApi.uploadPhoto(reportId, queuedPhoto);
          }

          await deleteQueuedReport(item.id);
        } catch {
          // Keep this item for the next retry.
        }
      }

      await refreshQueueCount();
    } finally {
      setSyncing(false);
    }
  }, [refreshQueueCount]);

  useEffect(() => {
    let active = true;

    const initialize = async () => {
      await migrateLegacyQueue();

      if (active) {
        await refreshQueueCount();
      }
    };

    void initialize();

    const handleOnline = () => {
      setOnline(true);
      void flushQueue();
    };

    const handleOffline = () => {
      setOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      active = false;
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [flushQueue, refreshQueueCount]);

  function locate() {
    if (!navigator.geolocation) {
      setMessage("Location is not available on this device.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) =>
        setCoords({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }),
      () => setMessage("Location permission was not granted. You can still submit the report."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  async function queueReport(draft: Draft): Promise<void> {
    await saveQueuedReport({
      id: createLocalId(),
      draft,
      photo: photo ?? undefined,
      photoName: photo?.name,
      photoType: photo?.type,
      createdAt: new Date().toISOString(),
    });

    await refreshQueueCount();

    setDescription("");
    setPhoto(null);

    setMessage(
      photo
        ? "Report and photo saved securely on this device. CRAM will submit them when connectivity returns."
        : "Report saved securely on this device. CRAM will submit it when connectivity returns.",
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    const draft: Draft = {
      hazard_type: hazard,
      description,
      consent_to_contact: false,
      ...(coords ?? {}),
    };

    if (!navigator.onLine) {
      try {
        await queueReport(draft);
      } catch {
        setMessage("Unable to save the report on this device.");
      }
      return;
    }

    try {
      const report = await citizenApi.submit(draft);

      if (photo) {
        try {
          await citizenApi.uploadPhoto(String(report.id), photo);
        } catch {
          // The report already exists. Queue only the outstanding photo
          // against the existing server report to avoid duplicate reports.
          await saveQueuedReport({
            id: createLocalId(),
            draft,
            photo,
            photoName: photo.name,
            photoType: photo.type,
            reportId: String(report.id),
            createdAt: new Date().toISOString(),
          });

          await refreshQueueCount();

          setDescription("");
          setPhoto(null);

          setMessage(
            `Report submitted. Reference: ${String(
              report.public_reference,
            )}. Photo upload is queued and will retry automatically.`,
          );

          return;
        }
      }

      setDescription("");
      setPhoto(null);
      setMessage(`Report submitted. Reference: ${String(report.public_reference)}`);
    } catch (error) {
      // A connectivity failure can occur after the browser believed it
      // was online. Preserve the complete report and photo for retry.
      if (!navigator.onLine) {
        try {
          await queueReport(draft);
          return;
        } catch {
          setMessage("Unable to save the report on this device.");
          return;
        }
      }

      setMessage(error instanceof Error ? error.message : "Unable to submit report.");
    }
  }

  return (
    <main className="citizen-report-page">
      <section className="citizen-report-card">
        <div className="citizen-report-heading">
          <p>Freetown Climate Risk Reporting</p>
          <h1>Report a climate hazard</h1>
          <p>
            Send a flood, heat, tree or other climate-risk observation to CRAM. GPS and a photo are
            optional.
          </p>
        </div>

        <div className="citizen-report-status">
          <span>{online ? "Online" : "Offline"}</span>
          <span>{queued} queued</span>
          {syncing && <span>Synchronizing...</span>}
        </div>

        <form onSubmit={submit}>
          <label>
            Hazard type
            <select value={hazard} onChange={(e) => setHazard(e.target.value)}>
              <option value="FLOOD">FLOOD</option>
              <option value="HEAT">HEAT</option>
              <option value="TREE">TREE</option>
              <option value="LANDSLIDE">LANDSLIDE</option>
              <option value="OTHER">OTHER</option>
            </select>
          </label>

          <label>
            Description
            <textarea
              required
              minLength={10}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What happened and what can you see?"
            />
          </label>

          <div className="citizen-report-location">
            <button type="button" onClick={locate}>
              Use my GPS
            </button>

            <span>
              {coords
                ? `${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`
                : "No location captured"}
            </span>
          </div>

          <label>
            Photo evidence (optional)
            <input
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
            />
          </label>

          <button type="submit">{online ? "Submit report" : "Save for later"}</button>

          {message && <p className="citizen-report-message">{message}</p>}
        </form>
      </section>
    </main>
  );
}
