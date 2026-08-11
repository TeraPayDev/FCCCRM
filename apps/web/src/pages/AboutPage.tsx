import { Link } from "react-router-dom";
import { PageHeader } from "../components/Page";

export function AboutPage() {
  return (
    <main className="about-page">
      <PageHeader
        eyebrow="About CRAM"
        title="Climate Risk Analytics Management Platform"
        description="CRAM is being developed as a governed municipal climate-risk and institutional data platform for Freetown City Council."
      />
      <section className="grid-2">
        <article className="card">
          <h2>Platform purpose</h2>
          <p className="card-subtitle">
            Bring institutional datasets, spatial information, governance workflows and climate
            analytics into one traceable platform.
          </p>
        </article>
        <article className="card">
          <h2>Current engineering position</h2>
          <p className="card-subtitle">
            The platform foundation and governed data platform are complete. ETL / processing is the
            next controlled engineering milestone.
          </p>
        </article>
      </section>
      <div style={{ marginTop: 16 }}>
        <Link className="button" to="/">
          Return to overview
        </Link>
      </div>
    </main>
  );
}
