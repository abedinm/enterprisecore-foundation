import { KeyRound } from "lucide-react";
import { Card } from "@/components/ui/Card";

export default function ApiKeysPage() {
  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><KeyRound className="size-6" /> API keys</h1>
      <Card className="p-6">
        <p className="text-sm text-zinc-500">
          API key management UI is scaffolded but the create/revoke endpoints are not yet implemented in this build.
          The data model (<code>APIKey</code> with hashed storage + prefix) is ready in the database.
        </p>
      </Card>
    </div>
  );
}
