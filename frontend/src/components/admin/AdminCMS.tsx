import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  Field,
  Modal,
  Spinner,
  TextArea,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";

interface Album {
  id: number;
  title: string;
  description: string | null;
  images: { id: number; image_url: string; caption: string | null }[];
}

interface Achievement {
  id: number;
  title: string;
  description: string | null;
  image_url: string | null;
  date: string | null;
  category: string | null;
}

interface NewsEvent {
  id: number;
  title: string;
  description: string | null;
  image_url: string | null;
  event_date: string | null;
  is_published: boolean;
}

type Tab = "gallery" | "achievements" | "news";

function CMSPage() {
  const [tab, setTab] = useState<Tab>("gallery");
  return (
    <>
      <p className="text-sm text-slate-500 font-semibold">
        Everything here appears on the public website instantly — no developer needed.
      </p>
      <div className="flex gap-2">
        {(
          [
            ["gallery", "Gallery Albums"],
            ["achievements", "Achievements"],
            ["news", "News & Events"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition ${
              tab === key ? "bg-indigo-600 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "gallery" && <GalleryTab />}
      {tab === "achievements" && <AchievementsTab />}
      {tab === "news" && <NewsTab />}
    </>
  );
}

/* ── Gallery ─────────────────────────────────────────────────────── */

function GalleryTab() {
  const toast = useToast();
  const [albums, setAlbums] = useState<Album[] | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [openAlbum, setOpenAlbum] = useState<Album | null>(null);

  const load = useCallback(async () => {
    try {
      setAlbums(await authFetch<Album[]>("/api/cms/albums"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load albums", "error");
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createAlbum = async () => {
    if (!title) return;
    try {
      await authFetch("/api/cms/albums", { method: "POST", body: { title, description: description || null } });
      toast("Album created");
      setTitle("");
      setDescription("");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const removeAlbum = async (album: Album) => {
    if (!confirm(`Delete album "${album.title}" and its photos?`)) return;
    try {
      await authFetch(`/api/cms/albums/${album.id}`, { method: "DELETE" });
      toast("Album deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  if (!albums) return <Spinner />;

  return (
    <>
      <div className="bg-white rounded-2xl border border-slate-100 p-4 flex flex-wrap gap-3 items-end">
        <Field label="New album title">
          <TextInput value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Annual Day 2026" />
        </Field>
        <Field label="Description">
          <TextInput value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Button onClick={createAlbum}>Create Album</Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {albums.map((album) => (
          <div key={album.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="aspect-video bg-slate-100">
              {album.images[0] && (
                <img src={album.images[0].image_url} alt={album.title} className="w-full h-full object-cover" />
              )}
            </div>
            <div className="p-4 space-y-1">
              <p className="font-extrabold text-slate-800">{album.title}</p>
              <p className="text-xs text-slate-500 font-semibold">{album.images.length} photos</p>
              <div className="flex gap-1 pt-1 text-sm -mx-2">
                <button
                  type="button"
                  className="px-2 py-2.5 rounded-lg text-indigo-600 font-bold hover:underline hover:bg-indigo-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                  onClick={() => setOpenAlbum(album)}
                >
                  Manage photos
                </button>
                <button
                  type="button"
                  className="px-2 py-2.5 rounded-lg text-rose-600 font-bold hover:underline hover:bg-rose-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
                  onClick={() => removeAlbum(album)}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {openAlbum && (
        <AlbumPhotosModal
          album={openAlbum}
          onClose={() => setOpenAlbum(null)}
          onChanged={() => load().then(() => setOpenAlbum(null))}
        />
      )}
    </>
  );
}

function AlbumPhotosModal({
  album,
  onClose,
  onChanged,
}: {
  album: Album;
  onClose: () => void;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [caption, setCaption] = useState("");

  const addImage = async () => {
    if (!url) return;
    try {
      await authFetch(`/api/cms/albums/${album.id}/images`, {
        method: "POST",
        body: { album_id: album.id, image_url: url, caption: caption || null },
      });
      toast("Photo added");
      setUrl("");
      setCaption("");
      onChanged();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const removeImage = async (imageId: number) => {
    try {
      await authFetch(`/api/cms/images/${imageId}`, { method: "DELETE" });
      toast("Photo removed");
      onChanged();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  return (
    <Modal title={`Photos — ${album.title}`} open onClose={onClose} wide>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {album.images.map((image) => (
          <div key={image.id} className="relative group">
            <img src={image.image_url} alt={image.caption ?? ""} className="w-full aspect-square object-cover rounded-xl" />
            <button
              type="button"
              aria-label="Remove photo"
              className="absolute top-1 right-1 w-11 h-11 flex items-center justify-center bg-rose-600 hover:bg-rose-700 text-white rounded-lg shadow focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700 transition"
              onClick={() => removeImage(image.id)}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
      <div className="pt-3 border-t border-slate-100 space-y-3">
        <Field label="Photo URL (paste a Cloudinary/hosted image link)">
          <TextInput value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
        </Field>
        <Field label="Caption (optional)">
          <TextInput value={caption} onChange={(e) => setCaption(e.target.value)} />
        </Field>
        <div className="flex justify-end">
          <Button onClick={addImage}>Add Photo</Button>
        </div>
      </div>
    </Modal>
  );
}

/* ── Achievements ────────────────────────────────────────────────── */

function AchievementsTab() {
  const toast = useToast();
  const [items, setItems] = useState<Achievement[] | null>(null);
  const [form, setForm] = useState({ title: "", description: "", image_url: "", date: "", category: "academics" });

  const load = useCallback(async () => {
    try {
      setItems(await authFetch<Achievement[]>("/api/cms/achievements"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (!form.title) return;
    try {
      await authFetch("/api/cms/achievements", {
        method: "POST",
        body: {
          title: form.title,
          description: form.description || null,
          image_url: form.image_url || null,
          date: form.date || null,
          category: form.category,
        },
      });
      toast("Achievement added");
      setForm({ title: "", description: "", image_url: "", date: "", category: "academics" });
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const remove = async (item: Achievement) => {
    if (!confirm(`Delete "${item.title}"?`)) return;
    try {
      await authFetch(`/api/cms/achievements/${item.id}`, { method: "DELETE" });
      toast("Deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  if (!items) return <Spinner />;

  const columns: Column<Achievement>[] = [
    { header: "Title", render: (a) => a.title },
    { header: "Category", render: (a) => a.category ?? "—" },
    { header: "Date", className: "whitespace-nowrap", render: (a) => formatDate(a.date) },
    {
      header: "Actions",
      render: (a) => (
        <button
          type="button"
          className="-mx-2 px-2 py-2.5 rounded-lg text-rose-600 font-bold hover:underline hover:bg-rose-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
          onClick={() => remove(a)}
        >
          Delete
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="bg-white rounded-2xl border border-slate-100 p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        <Field label="Title">
          <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Description">
          <TextInput value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Image URL">
          <TextInput value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
        </Field>
        <Field label="Date">
          <TextInput type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        </Field>
        <Button onClick={add}>Add</Button>
      </div>
      <DataTable columns={columns} rows={items} keyFor={(a) => a.id} />
    </>
  );
}

/* ── News & Events ───────────────────────────────────────────────── */

function NewsTab() {
  const toast = useToast();
  const [items, setItems] = useState<NewsEvent[] | null>(null);
  const [form, setForm] = useState({ title: "", description: "", event_date: "" });

  const load = useCallback(async () => {
    try {
      setItems(await authFetch<NewsEvent[]>("/api/cms/news"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (!form.title) return;
    try {
      await authFetch("/api/cms/news", {
        method: "POST",
        body: {
          title: form.title,
          description: form.description || null,
          event_date: form.event_date || null,
          is_published: true,
        },
      });
      toast("Event added");
      setForm({ title: "", description: "", event_date: "" });
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const remove = async (item: NewsEvent) => {
    if (!confirm(`Delete "${item.title}"?`)) return;
    try {
      await authFetch(`/api/cms/news/${item.id}`, { method: "DELETE" });
      toast("Deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  if (!items) return <Spinner />;

  const columns: Column<NewsEvent>[] = [
    { header: "Title", render: (n) => n.title },
    { header: "Event date", className: "whitespace-nowrap", render: (n) => formatDate(n.event_date) },
    { header: "Published", render: (n) => (n.is_published ? "Yes" : "No") },
    {
      header: "Actions",
      render: (n) => (
        <button
          type="button"
          className="-mx-2 px-2 py-2.5 rounded-lg text-rose-600 font-bold hover:underline hover:bg-rose-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
          onClick={() => remove(n)}
        >
          Delete
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="bg-white rounded-2xl border border-slate-100 p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <Field label="Title">
          <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Description">
          <TextInput value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Event date">
          <TextInput type="date" value={form.event_date} onChange={(e) => setForm({ ...form, event_date: e.target.value })} />
        </Field>
        <Button onClick={add}>Add</Button>
      </div>
      <DataTable columns={columns} rows={items} keyFor={(n) => n.id} />
    </>
  );
}

export default function AdminCMS() {
  return (
    <PortalShell portal="admin" title="Website Content Manager">
      <CMSPage />
    </PortalShell>
  );
}
