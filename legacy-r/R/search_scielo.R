#' Search SciELO and return results as a data.frame
#'
#' Executes a search in the SciELO database using multiple optional filters,
#' and returns the results as a data frame.
#'
#' Note: Only one value per filter category is currently supported (e.g., only one language).
#'
#' @param query Search term (e.g., "climate change"). Required.
#' @param lang Interface language for SciELO website ("en", "es", "pt"). Default is "en".
#' @param lang_operator Operator for combining language filters ("AND" or "OR"). Default is "AND".
#' @param n_max Maximum number of results to return. Optional.
#' @param journals Vector of journal names to filter. Only one supported. Optional.
#' @param collections A character string for filtering by SciELO collection (country name or ISO code, e.g., "Mexico" or "mex").
#' @param languages Vector of article languages to filter (e.g., "en").
#' @param categories Vector of subject categories (e.g., "ecology").
#' @param year_start Start year for filtering articles. Optional.
#' @param year_end End year for filtering articles. Optional.
#'
#' @return A data.frame with the search results.
#' @export
#'
#' @examplesIf interactive()
#' \donttest{
#' # Simple search with a keyword
#' df1 <- search_scielo("salud ambiental")
#'
#' # Limit number of results to 5
#' df2 <- search_scielo("salud ambiental", n_max = 5)
#'
#' # Filter by SciELO collection (country name or code)
#' df3 <- search_scielo("salud ambiental", collections = "Ecuador")
#' df4 <- search_scielo("salud ambiental", collections = "cri")  # Costa Rica by ISO code
#'
#' # Filter by article language
#' df5 <- search_scielo("salud ambiental", languages = "es")
#'
#' # Filter by a specific journal
#' df6 <- search_scielo("salud ambiental", journals = "Revista Ambiente & Agua")
#'
#' # Filter by subject category
#' df7 <- search_scielo("salud ambiental", categories = "environmental sciences")
#'
#' # Filter by year range
#' df8 <- search_scielo("salud ambiental", year_start = 2015, year_end = 2020)
#' }
search_scielo <- function(query,
                          lang = "en",
                          lang_operator = "AND",
                          n_max = NULL,
                          journals = NULL,
                          collections = NULL,
                          languages = NULL,
                          categories = NULL,
                          year_start = NULL,
                          year_end = NULL) {
  
  # ---------------------------
  # Input validations
  # ---------------------------
  
  if (missing(query) || !is.character(query) || nchar(query) < 2) {
    stop("The 'query' parameter must be a non-empty character string.", call. = FALSE)
  }
  
  if (!lang %in% c("en", "es", "pt")) {
    stop("The 'lang' parameter must be one of: 'en', 'es', 'pt'.", call. = FALSE)
  }
  
  if (!lang_operator %in% c("AND", "OR")) {
    stop("The 'lang_operator' parameter must be either 'AND' or 'OR'.", call. = FALSE)
  }
  
  # Inside search_scielo
  year_vals <- NULL
  if (!is.null(year_start) && !is.null(year_end)) {
    year_vals <- years(year_start, year_end)
  } else if (!is.null(year_start) || !is.null(year_end)) {
    stop("Both 'year_start' and 'year_end' must be provided together.", call. = FALSE)
  }
  
  # ---------------------------
  # Build internal query object
  # ---------------------------
  
  query_obj <- structure(
    list(
      query = query,
      lang = lang,
      n_max = normalize_nmax(n_max),
      lang_operator = lang_operator,
      languages = if (is.null(languages)) character() else normalize_languages(languages),
      collections = if (is.null(collections)) character() else normalize_collections(as.character(collections)),
      categories = if (is.null(categories)) character() else normalize_categories(categories),
      journals   = if (is.null(journals)) character() else normalize_journals(journals),
      year_start = if (!is.null(year_vals)) year_vals$year_start else NULL,
      year_end = if (!is.null(year_vals)) year_vals$year_end else NULL
    ),
    class = "scielo_query"
  )
  
  # ---------------------------
  # Perform scraping and return results
  # ---------------------------
  
  return(fetch_scielo_results(query_obj))
}
