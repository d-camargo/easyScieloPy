#' @importFrom utils URLencode
# Helper function: build_filter
build_filter <- function(param, values) {
  if (length(values) == 0) return("")
  paste0("&", paste0("filter%5B", param, "%5D%5B%5D=", vapply(values, URLencode, character(1)), collapse = ""))
}

# Helper function: build_operator
build_operator <- function(param, op, values_count = 0) {
  if (values_count > 1 || (values_count == 1 && op != "AND")) { # Assuming "AND" is default and might not need explicit operator for single value
    return(paste0("&filter_boolean_operator%5B", param, "%5D%5B%5D=", op))
  }
  return("")
}

# Helper function: build_year_filter
build_year_filter <- function(start_year, end_year) {
  if (is.null(start_year) || is.null(end_year)) return("")
  if (!is.numeric(start_year) || !is.numeric(end_year) || start_year > end_year) {
    warning("Invalid year range provided for URL. Skipping year filter.", call. = FALSE)
    return("")
  }
  years <- seq(from = floor(start_year), to = floor(end_year))
  paste0(paste0("&filter%5Byear_cluster%5D%5B%5D=", years), collapse = "")
}

#' Builds a SciELO search URL based on query object parameters.
#' @param query_obj A 'scielo_query' object.
#' @param page_from_idx The 'from' index for pagination (e.g., 1, 16, 31).
#' @param items_per_page The 'count' parameter (e.g., 15).
#' @return A character string representing the full SciELO search URL.
#' @keywords internal
build_scielo_url <- function(query_obj, page_from_idx, items_per_page) {
  base_url <- "https://search.scielo.org/"
  encoded_query <- URLencode(query_obj$query)
  
  # Combine filters into one string
  filters <- paste0(
    build_filter("in", query_obj$collections),
    build_filter("journal_title", query_obj$journals),
    build_filter("la", query_obj$languages),
    build_operator("la", query_obj$lang_operator, length(query_obj$languages)),
    build_filter("wok_subject_categories", query_obj$categories),
    build_year_filter(query_obj$year_start, query_obj$year_end)
  )
  
  url <- paste0(
    base_url,
    "?lang=", query_obj$lang,
    "&count=", items_per_page,
    "&from=", page_from_idx,
    "&output=site&format=summary&sort=&fb=&page=", ceiling(page_from_idx / items_per_page),
    "&q=", encoded_query,
    filters
  )
  return(url)
}