-- Run once in the Supabase SQL Editor (Project -> SQL Editor -> New query).
-- Holds the cleaned TRAINING rows only; the final test set never goes to Supabase.

create table if not exists public.listings_train (
    listing_id             bigint primary key,
    brand                  text not null,
    model                  text,
    model_group            text,
    item_type              text,
    product_type           text,
    condition              text,
    condition_rank         smallint,
    asking_price           numeric,
    estimated_retail_price numeric,
    asking_price_ratio     numeric,
    has_target             boolean,
    production_year        smallint,
    item_age_years         smallint,
    age_band               text,
    year_is_lower_bound    boolean,
    year_source            text,
    brand_code             text,
    accessories            text,
    accessories_known      boolean,
    has_dust_bag           boolean,
    has_strap              boolean,
    has_authenticity_card  boolean,
    exterior_material      text,
    exterior_color         text,
    hardware_color         text,
    size                   text,
    available              boolean,
    listed_at              date,
    days_listed            integer,
    recent                 boolean,
    dropship_partner       boolean,
    possible_duplicate     boolean,
    url                    text
);

-- The dashboard reads with the public (publishable / anon) key, so allow read-only access.
-- Writes need the secret key, which bypasses row level security and stays in your local .env.
alter table public.listings_train enable row level security;

drop policy if exists "Public read access" on public.listings_train;
create policy "Public read access" on public.listings_train
    for select to anon, authenticated using (true);
