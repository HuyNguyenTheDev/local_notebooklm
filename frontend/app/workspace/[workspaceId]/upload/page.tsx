import { redirect } from "next/navigation";

type UploadPageProps = {
  params: Promise<{
    workspaceId: string;
  }>;
};

export default async function WorkspaceUploadPage({ params }: UploadPageProps) {
  const { workspaceId } = await params;
  redirect(`/workspace/${workspaceId}`);
}
