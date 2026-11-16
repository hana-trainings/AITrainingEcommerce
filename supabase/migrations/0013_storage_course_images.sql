-- 0013_storage_course_images.sql
-- A Supabase Storage bucket for course pictures (US-703 AC3, NFR-SEC-16).
-- Public read (anyone can see a course image), only staff/owner can upload or change files.

-- The bucket itself enforces size and type, even if the app's checks are bypassed:
--   2 MB max (2 * 1024 * 1024 bytes) and only JPG, PNG or WebP.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('course-images', 'course-images', true, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
   set public             = excluded.public,
       file_size_limit    = excluded.file_size_limit,
       allowed_mime_types = excluded.allowed_mime_types;

-- Storage files are rows in storage.objects, which already has RLS switched on by Supabase.

-- Anyone, including guests, can read course images so the catalog can show them.
create policy course_images_public_read on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'course-images');

-- Staff and owner can upload images, and only with an image file extension (belt and braces with the MIME check).
create policy course_images_staff_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'course-images'
    and (select public.is_staff())
    and lower(storage.extension(name)) in ('jpg', 'jpeg', 'png', 'webp')
  );

-- Staff and owner can replace an existing course image (same extension rule).
create policy course_images_staff_update on storage.objects
  for update to authenticated
  using (bucket_id = 'course-images' and (select public.is_staff()))
  with check (
    bucket_id = 'course-images'
    and (select public.is_staff())
    and lower(storage.extension(name)) in ('jpg', 'jpeg', 'png', 'webp')
  );

-- Staff and owner can delete course images, e.g. when a picture is replaced.
create policy course_images_staff_delete on storage.objects
  for delete to authenticated
  using (bucket_id = 'course-images' and (select public.is_staff()));
