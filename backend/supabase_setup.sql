create extension if not exists vector;

create table documents (
  id bigserial primary key,
  content text,
  embedding vector(1024),
  filename text
);

create or replace function match_documents(query_embedding vector(1024), match_count int, filter_filename text)
returns table(content text, similarity float)
language sql stable as $$
  select content, 1 - (embedding <=> query_embedding) as similarity
  from documents
  where filename = filter_filename
  order by embedding <=> query_embedding
  limit match_count;
$$;

create table chat_history (
  id bigserial primary key,
  session_id text,
  role text,
  content text,
  created_at timestamp default now()
);
