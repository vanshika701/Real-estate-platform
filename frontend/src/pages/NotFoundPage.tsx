import { Link } from "react-router-dom";

import { EmptyState } from "../components/States";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <EmptyState
        title="Page not found"
        description="The page you're looking for doesn't exist."
        action={
          <Link to="/" className="btn-primary">
            Go home
          </Link>
        }
      />
    </div>
  );
}

/** Stand-in for screens built in the next phase, so routes and role guards already work. */
export function ComingSoonPage({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <EmptyState title={title} description="This screen is being built next." />
    </div>
  );
}
