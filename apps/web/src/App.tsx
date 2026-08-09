import { useEffect, useState } from "react";

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

function App() {
  const [apiStatus, setApiStatus] = useState("Checking...");

  useEffect(() => {
    const apiUrl =
      import.meta.env.VITE_API_URL ?? "http://10.1.11.7:8000";

    fetch(`${apiUrl}/api/v1/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("API unavailable");
        }
        return response.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        setApiStatus(`${data.status} (${data.version})`);
      })
      .catch(() => {
        setApiStatus("Unavailable");
      });
  }, []);

  return (
    <main>
      <h1>CRAM Platform</h1>

      <p>Climate Risk Analytics Management Platform</p>

      <hr />

      <h2>Development Environment</h2>

      <p>
        <strong>Frontend:</strong> Running
      </p>

      <p>
        <strong>API:</strong> {apiStatus}
      </p>
    </main>
  );
}

export default App;
