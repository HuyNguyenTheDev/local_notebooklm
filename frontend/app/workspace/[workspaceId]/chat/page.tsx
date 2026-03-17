import { redirect } from "next/navigation";

type ChatPageProps = {
  params: Promise<{
    workspaceId: string;
  }>;
};

export default async function WorkspaceChatPage({ params }: ChatPageProps) {
  const { workspaceId } = await params;
  redirect(`/workspace/${workspaceId}`);
}
