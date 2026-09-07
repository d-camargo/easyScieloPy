#' Validate year range for SciELO query
#'
#' Ensures that start and end years are valid numeric values and in correct order.
#'
#' @param start_year Integer. Start year for filtering (inclusive).
#' @param end_year Integer. End year for filtering (inclusive).
#'
#' @return A list with named elements `year_start` and `year_end`.
#' @export
#'
#' @examples
#' valid_years <- years(2018, 2022)
years <- function(start_year, end_year) {
  # Check missing
  if (missing(start_year) || missing(end_year)) {
    stop("Both 'start_year' and 'end_year' must be provided.", call. = FALSE)
  }
  
  # Check types
  if (!is.numeric(start_year) || start_year %% 1 != 0) {
    stop("'start_year' must be an integer number.", call. = FALSE)
  }
  
  if (!is.numeric(end_year) || end_year %% 1 != 0) {
    stop("'end_year' must be an integer number.", call. = FALSE)
  }
  
  # Check plausible year range (adjust as needed)
  current_year <- as.integer(format(Sys.Date(), "%Y"))
  if (start_year < 1500 || start_year > current_year) {
    stop(paste0("'start_year' must be between 1500 and ", current_year, "."), call. = FALSE)
  }
  
  if (end_year < 1500 || end_year > current_year) {
    stop(paste0("'end_year' must be between 1500 and ", current_year, "."), call. = FALSE)
  }
  
  # Check order
  if (start_year > end_year) {
    stop("'start_year' must be less than or equal to 'end_year'.", call. = FALSE)
  }
  
  return(list(
    year_start = as.integer(start_year),
    year_end = as.integer(end_year)
  ))
}
