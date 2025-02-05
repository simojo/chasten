"""💫 Chasten checks the AST of a Python program."""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Union

import typer
from pyastgrep import search as pyastgrepsearch  # type: ignore

from chasten import (
    checks,
    configApp,
    configuration,
    constants,
    createchecks,
    database,
    debug,
    enumerations,
    filesystem,
    output,
    process,
    results,
    server,
    util,
)

# create a Typer object to support the command-line interface
cli = typer.Typer(no_args_is_help=True)
app = configApp.config_App()
# create a small bullet for display in the output
small_bullet_unicode = constants.markers.Small_Bullet_Unicode
CHECK_STORAGE = constants.chasten.App_Storage
API_KEY_STORAGE = constants.chasten.API_Key_Storage
ANALYSIS_FILE = constants.chasten.Analyze_Storage


# ---
# Region: Helper functions {{{
# ---


def output_preamble(
    verbose: bool,
    debug_level: debug.DebugLevel = debug.DebugLevel.ERROR,
    debug_destination: debug.DebugDestination = debug.DebugDestination.CONSOLE,
    **kwargs,
) -> None:
    """Output all of the preamble content."""
    # setup the console and the logger through the output module
    output.setup(debug_level, debug_destination)
    output.logger.debug(f"Display verbose output? {verbose}")
    output.logger.debug(f"Debug level? {debug_level.value}")
    output.logger.debug(f"Debug destination? {debug_destination.value}")
    # display the header
    output.print_header()
    # display details about configuration as
    # long as verbose output was requested;
    # note that passing **kwargs to this function
    # will pass along all of the extra keyword
    # arguments that were input to the function
    output.print_diagnostics(
        verbose,
        debug_level=debug_level.value,
        debug_destination=debug_destination.value,
        **kwargs,
    )


def display_serve_or_publish_details(
    label: str,
    database_path: Path,
    metadata: Path,
    port: int = 8001,
    publish: bool = False,
) -> None:
    """Display diagnostic details at startup of serve or publish commands."""
    # output diagnostic information about the datasette instance
    output.console.print()
    output.console.print(label)
    output.console.print(
        f"{constants.markers.Indent}{small_bullet_unicode} Database: '{output.shorten_file_name(str(database_path), 120)}'"
    )
    output.console.print(
        f"{constants.markers.Indent}{small_bullet_unicode} Metadata: '{output.shorten_file_name(str(metadata), 120)}'"
    )
    # do not display a port if the task is publishing to fly.io
    # because that step does not support port specification
    if not publish:
        output.console.print(
            f"{constants.markers.Indent}{small_bullet_unicode} Port: {port}"
        )


# ---
# End region: Helper functions }}}
# ---

# ---
# Start region: Command-line interface functions {{{
# ---


@cli.command()
def create_checks(
    filename: Path = typer.Option("checks.yml", help="YAML file name")
) -> None:
    """🔧 Interactively specify for checks and have a checks.yml file created(Requires API key)"""
    # creates a textual object for better user interface
    app.run()
    # Checks if the file storing the wanted checks exists and is valid
    if filesystem.confirm_valid_file(CHECK_STORAGE):
        # stores the human readable version of the checks
        result = configApp.write_checks(configApp.split_file(CHECK_STORAGE))
        # Checks if API key storage file exists
        if filesystem.confirm_valid_file(API_KEY_STORAGE):
            # prints the human readable checks to the terminal
            output.console.print(result)
            # loads the decrypted API Key
            api_key = createchecks.load_user_api_key(API_KEY_STORAGE)
            # calls the function to generate the yaml file
            output.console.print(
                createchecks.generate_yaml_config(filename, api_key, result)
            )
        else:
            # prompts the user to input there API key to the terminal
            api_key = input("Please Enter your openai API Key:")
            # If not a valid API key prompts user again
            while not createchecks.is_valid_api_key(api_key):
                output.console.print(
                    "[red][ERROR][/red] Invalid API key. Please enter a valid API key."
                )
                api_key = input("Please Enter your openai API Key:")
            # stores the API key in a file
            createchecks.save_user_api_key(api_key)
            # prints the human readable checks to the terminal
            output.console.print(result)
            # gets the decrypted API Key
            api_key = createchecks.load_user_api_key(API_KEY_STORAGE)
            # prints the generated YAML file to the terminal
            output.console.print(
                createchecks.generate_yaml_config(filename, api_key, result)
            )
    else:
        # displays an error message if the CHECK_STORAGE file does not exist
        output.console.print(
            f"[red][ERROR][/red] No {CHECK_STORAGE} file exists\n  - Rerun the command and specify checks"
        )


@cli.command()
def configure(  # noqa: PLR0913
    task: enumerations.ConfigureTask = typer.Argument(
        enumerations.ConfigureTask.VALIDATE.value
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="A directory with configuration file(s), path to configuration file, or URL to configuration file.",
    ),
    debug_level: debug.DebugLevel = typer.Option(
        debug.DebugLevel.ERROR.value,
        "--debug-level",
        "-l",
        help="Specify the level of debugging output.",
    ),
    debug_destination: debug.DebugDestination = typer.Option(
        debug.DebugDestination.CONSOLE.value,
        "--debug-dest",
        "-t",
        help="Specify the destination for debugging output.",
    ),
    force: bool = typer.Option(
        False,
        help="Create configuration directory and files even if they exist",
    ),
    verbose: bool = typer.Option(False, help="Display verbose debugging output"),
) -> None:
    """🪂 Manage chasten's configuration."""
    # output the preamble, including extra parameters specific to this function
    output_preamble(
        verbose,
        debug_level,
        debug_destination,
        task=task.value,
        config=config,
        force=force,
    )
    # setup the console and the logger through the output module
    output.setup(debug_level, debug_destination)
    output.logger.debug(f"Display verbose output? {verbose}")
    output.logger.debug(f"Debug level? {debug_level.value}")
    output.logger.debug(f"Debug destination? {debug_destination.value}")
    # display the configuration directory and its contents
    if task == enumerations.ConfigureTask.VALIDATE:
        # validate the configuration files:
        # --> config.yml (or url pointing to one)
        # --> checks.yml (or whatever file/url is reference in config.yml)
        (validated, _) = configuration.validate_configuration_files(config, verbose)
        # some aspect of the configuration was not
        # valid, so exit early and signal an error
        if not validated:
            output.console.print(
                "\n:person_shrugging: Cannot perform analysis due to configuration error(s).\n"
            )
            sys.exit(constants.markers.Non_Zero_Exit)
    # create the configuration directory and a starting version of the configuration file
    if task == enumerations.ConfigureTask.CREATE:
        # attempt to create the configuration directory
        try:
            # create the configuration directory, which will either be the one
            # specified by the config parameter (if it exists) or it will be
            # the one in the platform-specific directory given by platformdirs
            if config is None:
                configuration_directory = None
            else:
                configuration_directory = Path(config)
            created_directory_path = filesystem.create_configuration_directory(
                configuration_directory, force
            )
            # write the configuration file for the chasten tool in the created directory
            filesystem.create_configuration_file(
                created_directory_path,
                constants.filesystem.Main_Configuration_File,
            )
            # write the check file for the chasten tool in the created directory
            filesystem.create_configuration_file(
                created_directory_path, constants.filesystem.Main_Checks_File
            )
            # display diagnostic information about the completed process
            output.console.print(
                f":sparkles: Created configuration directory and file(s) in {created_directory_path}"
            )
        # cannot re-create the configuration directory, so display
        # a message and suggest the use of --force the next time;
        # exit early and signal an error with a non-zero exist code
        except FileExistsError:
            if not force:
                output.console.print(
                    "\n:person_shrugging: Configuration directory already exists."
                )
                output.console.print(
                    "Use --force to recreate configuration directory and its containing files."
                )
            sys.exit(constants.markers.Non_Zero_Exit)


@cli.command()
def analyze(  # noqa:  PLR0912, PLR0913, PLR0915
    project: str = typer.Argument(help="Name of the project."),
    xpath: Path = typer.Option(
        str,
        "--xpath-version",
        "-xp",
        help="Accepts different xpath version, runs xpath version two by default.",
    ),
    check_include: Tuple[enumerations.FilterableAttribute, str, int] = typer.Option(
        (None, None, 0),
        "--check-include",
        "-i",
        help="Attribute name, value, and match confidence level for inclusion.",
    ),
    check_exclude: Tuple[enumerations.FilterableAttribute, str, int] = typer.Option(
        (None, None, 0),
        "--check-exclude",
        "-e",
        help="Attribute name, value, and match confidence level for exclusion.",
    ),
    input_path: Path = typer.Option(
        filesystem.get_default_directory_list(),
        "--search-path",
        "-d",
        help="A path (i.e., directory or file) with Python source code(s).",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        resolve_path=True,
    ),
    output_directory: Path = typer.Option(
        None,
        "--save-directory",
        "-s",
        help="A directory for saving output file(s).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    store_result: Path = typer.Option(
        None,
        "--markdown-storage",
        "-r",
        help="A directory for storing results in a markdown file",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="A directory with configuration file(s) or URL to configuration file.",
    ),
    debug_level: debug.DebugLevel = typer.Option(
        debug.DebugLevel.ERROR.value,
        "--debug-level",
        "-l",
        help="Specify the level of debugging output.",
    ),
    debug_destination: debug.DebugDestination = typer.Option(
        debug.DebugDestination.CONSOLE.value,
        "--debug-dest",
        "-t",
        help="Specify the destination for debugging output.",
    ),
    display: bool = typer.Option(False, help="Display results using frogmouth"),
    verbose: bool = typer.Option(False, help="Enable verbose mode output."),
    save: bool = typer.Option(False, help="Enable saving of output file(s)."),
    force: bool = typer.Option(False, help="Force creation of new markdown file"),
) -> None:
    """💫 Analyze the AST of Python source code."""
    # setup the console and the logger through the output module
    output.setup(debug_level, debug_destination)
    output.logger.debug(f"Display verbose output? {verbose}")
    output.logger.debug(f"Debug level? {debug_level.value}")
    output.logger.debug(f"Debug destination? {debug_destination.value}")
    start_time = time.time()
    output.logger.debug("Analysis Started.")
    # output the preamble, including extra parameters specific to this function
    output_preamble(
        verbose,
        debug_level,
        debug_destination,
        project=project,
        directory=input_path,
    )
    # extract the current version of the program
    chasten_version = util.get_chasten_version()
    # display current chasten version
    output.logger.debug(f"Current version of chasten: {chasten_version}")
    # create the include and exclude criteria
    include = results.CheckCriterion(
        attribute=str(checks.fix_check_criterion(check_include[0])),
        value=str(checks.fix_check_criterion(check_include[1])),
        confidence=int(checks.fix_check_criterion(check_include[2])),
    )
    exclude = results.CheckCriterion(
        attribute=str(checks.fix_check_criterion(check_exclude[0])),
        value=str(checks.fix_check_criterion(check_exclude[1])),
        confidence=int(checks.fix_check_criterion(check_exclude[2])),
    )
    # create a configuration that is the same for all results
    chasten_configuration = results.Configuration(
        chastenversion=chasten_version,
        projectname=project,
        configdirectory=Path(config),
        searchpath=input_path,
        debuglevel=debug_level,
        debugdestination=debug_destination,
        checkinclude=include,
        checkexclude=exclude,
    )
    # connect the configuration to the top-level chasten object for results saving
    # note: this is the final object that contains all of the data
    chasten_results_save = results.Chasten(configuration=chasten_configuration)
    # add extra space after the command to run the program
    output.console.print()
    # validate the configuration
    (validated, checks_dict) = configuration.validate_configuration_files(
        config, verbose
    )
    # some aspect of the configuration was not
    # valid, so exit early and signal an error
    if not validated:
        output.console.print(
            "\n:person_shrugging: Cannot perform analysis due to configuration error(s).\n"
        )
        output.logger.debug("Cannot perform analysis due to configuration error(s)")
        sys.exit(constants.markers.Non_Zero_Exit)
    # extract the list of the specific patterns (i.e., the XPATH expressions)
    # that will be used to analyze all of the XML-based representations of
    # the Python source code found in the valid directories
    check_list: List[Dict[str, Union[str, Dict[str, int]]]] = checks_dict[
        constants.checks.Checks_Label
    ]
    # filter the list of checks based on the include and exclude parameters
    # --> only run those checks that were included
    check_list = process.include_or_exclude_checks(  # type: ignore
        check_list, include=True, *check_include
    )
    # --> remove those checks that were excluded
    check_list = process.include_or_exclude_checks(  # type: ignore
        check_list, include=False, *check_exclude
    )
    # the specified search path is not valid and thus it is
    # not possible to analyze the Python source files in this directory
    # OR
    # the specified search path is not valid and thus it is
    # not possible to analyze the specific Python source code file
    if not filesystem.confirm_valid_directory(
        input_path
    ) and not filesystem.confirm_valid_file(input_path):
        output.console.print(
            "\n:person_shrugging: Cannot perform analysis due to invalid search directory.\n"
        )
        sys.exit(constants.markers.Non_Zero_Exit)
    if store_result:
        # creates an empty string for storing results temporarily
        analysis_result = ""
        analysis_file_dir = store_result / ANALYSIS_FILE
        # clears markdown file of results if it exists and new results are to be store
        if filesystem.confirm_valid_file(analysis_file_dir):
            if not force:
                if display:
                    database.display_results_frog_mouth(
                        analysis_file_dir, util.get_OS()
                    )
                    sys.exit(0)
                else:
                    output.console.print(
                        "File already exists: use --force to recreate markdown directory."
                    )
                    sys.exit(constants.markers.Non_Zero_Exit)
            else:
                analysis_file_dir.write_text("")
        # creates file if doesn't exist already
        analysis_file_dir.touch()
    # create the list of directories
    valid_directories = [input_path]
    # output the list of directories subject to checking
    output.console.print()
    output.console.print(f":sparkles: Analyzing Python source code in: {input_path}")
    # output the number of checks that will be performed
    output.console.print()
    output.console.print(f":tada: Performing {len(check_list)} check(s):")
    output.console.print()
    # create a check_status list for all of the checks
    check_status_list: List[bool] = []
    # check XPATH version
    if xpath == "1.0":
        output.logger.debug("Using XPath version 1.0")
    else:
        output.logger.debug("Using XPath version 2.0")
    # iterate through and perform each of the checks
    for current_check in check_list:
        # extract the pattern for the current check
        current_xpath_pattern = str(
            current_check[constants.checks.Check_Pattern]
        )  # type: ignore
        # extract the minimum and maximum values for the checks, if they exist
        # note that this function will return None for a min or a max if
        # that attribute does not exist inside of the current_check; importantly,
        # having a count or a min or a max is all optional in a checks file
        (min_count, max_count) = checks.extract_min_max(current_check)
        # extract details about the check to display in the header
        # of the syntax box for this specific check
        check_id = current_check[constants.checks.Check_Id]  # type: ignore
        output.logger.debug(f"check id: {check_id}")
        check_name = current_check[constants.checks.Check_Name]  # type: ignore
        check_description = checks.extract_description(current_check)
        # search for the XML contents of an AST that match the provided
        # XPATH query using the search_python_file in search module of pyastgrep;
        # this looks for matches across all path(s) in the specified source path
        # match_generator = pyastgrepsearch.search_python_files(
        #         paths=valid_directories, expression=current_xpath_pattern, xpath2=True
        # )
        if xpath == "1.0":
            match_generator = pyastgrepsearch.search_python_files(
                paths=valid_directories, expression=current_xpath_pattern, xpath2=False
            )
        else:
            match_generator = pyastgrepsearch.search_python_files(
                paths=valid_directories, expression=current_xpath_pattern, xpath2=True
            )
        # materia>>> mastlize a list from the generator of (potential) matches;
        # note that this list will also contain an object that will
        # indicate that the analysis completed for each located file
        match_generator_list = list(match_generator)
        # filter the list of matches so that it only includes
        # those that are a Match object that will contain source code
        (match_generator_list, _) = process.filter_matches(
            match_generator_list, pyastgrepsearch.Match
        )
        # organize the matches according to the file to which they
        # correspond so that processing of matches takes place per-file
        match_dict = process.organize_matches(match_generator_list)
        # perform an enforceable check if it is warranted for this check
        current_check_save = None
        if checks.is_checkable(min_count, max_count):
            # determine whether or not the number of found matches is within mix and max
            check_status = checks.check_match_count(
                len(match_generator_list), min_count, max_count
            )
            # keep track of the outcome for this check
            check_status_list.append(check_status)
        # this is not an enforceable check and thus the tool always
        # records that the checked passed as a default
        else:
            check_status = True
        # convert the status of the check to a visible symbol for display
        check_status_symbol = util.get_symbol_boolean(check_status)
        # escape the open bracket symbol that may be in an XPATH expression
        # and will prevent it from displaying correctly
        current_xpath_pattern_escape = current_xpath_pattern.replace("[", "\\[")
        # display minimal diagnostic output
        output.console.print(
            f"  {check_status_symbol} id: '{check_id}', name: '{check_name}'"
            + f", pattern: '{current_xpath_pattern_escape}', min={min_count}, max={max_count}"
        )
        if store_result:
            # makes the check marks or x's appear as words instead for markdown
            check_pass = (
                "PASSED:"
                if check_status_symbol == "[green]\u2713[/green]"
                else "FAILED:"
            )
            # stores check type in a string to stored in file later
            analysis_result += (
                f"\n# {check_pass} **ID:** '{check_id}', **Name:** '{check_name}'"
                + f", **Pattern:** '{current_xpath_pattern_escape}', min={min_count}, max={max_count}\n\n"
            )

        # for each potential match, log and, if verbose model is enabled,
        # display details about each of the matches
        current_result_source = results.Source(
            filename=str(str(vd) for vd in valid_directories)
        )
        # there were no matches and thus the current_check_save of None
        # should be recorded inside of the source of the results
        if len(match_generator_list) == 0:
            current_result_source.check = current_check_save
        # iteratively analyze:
        # a) A specific file name
        # b) All of the matches for that file name
        # Note: the goal is to only process matches for a
        # specific file, ensuring that matches for different files
        # are not mixed together, which would contaminate the results
        # Note: this is needed because using pyastgrepsearch will
        # return results for all of the files that matched the check
        for file_name, matches_list in match_dict.items():
            # create the current check
            current_check_save = results.Check(
                id=check_id,  # type: ignore
                name=check_name,  # type: ignore
                description=check_description,  # type: ignore
                min=min_count,  # type: ignore
                max=max_count,  # type: ignore
                pattern=current_xpath_pattern,
                passed=check_status,
            )
            # create a source that is solely for this file name
            current_result_source = results.Source(filename=file_name)
            # put the current check into the list of checks in the current source
            current_result_source.check = current_check_save
            # display minimal diagnostic output
            output.console.print(
                f"    {small_bullet_unicode} {file_name} - {len(matches_list)} matches"
            )
            if store_result:
                # stores details of checks in string to be stored later
                analysis_result += f"    - {file_name} - {len(matches_list)} matches\n"
            # extract the lines of source code for this file; note that all of
            # these matches are organized for the same file and thus it is
            # acceptable to extract the lines of the file from the first match
            # a long as there are matches available for analysis
            if len(matches_list) > 0:
                current_result_source._filelines = matches_list[0].file_lines
            # iterate through all of the matches that are specifically
            # connected to this source that is connected to a specific file name
            for current_match in matches_list:
                if isinstance(current_match, pyastgrepsearch.Match):
                    current_result_source._filelines = current_match.file_lines
                    # extract the direct line number for this match
                    position_end = current_match.position.lineno
                    # extract the column offset for this match
                    column_offset = current_match.position.col_offset
                    # create a match specifically for this file;
                    # note that the AST starts line numbering at 1 and
                    # this means that storing the matching line requires
                    # the indexing of file_lines with position_end - 1;
                    # note also that linematch is the result of using
                    # lstrip to remove any blank spaces before the code
                    current_match_for_current_check_save = results.Match(
                        lineno=position_end,
                        coloffset=column_offset,
                        linematch=current_match.file_lines[position_end - 1].lstrip(
                            constants.markers.Space
                        ),
                        linematch_context=util.join_and_preserve(
                            current_match.file_lines,
                            max(
                                0,
                                position_end - constants.markers.Code_Context,
                            ),
                            position_end + constants.markers.Code_Context,
                        ),
                    )
                    # save the entire current_match that is an instance of
                    # pyastgrepsearch.Match for verbose debugging output as needed
                    current_check_save._matches.append(current_match)
                    # add the match to the listing of matches for the current check
                    current_check_save.matches.append(
                        current_match_for_current_check_save
                    )  # type: ignore
            # add the current source to main object that contains a list of source
            chasten_results_save.sources.append(current_result_source)
        # add the amount of total matches in each check to the end of each checks output
        output.console.print(f"   = {len(match_generator_list)} total matches\n")
    # calculate the final count of matches found
    total_result = util.total_amount_passed(check_status_list)
    # display checks passed, total amount of checks, and percentage of checks passed
    output.console.print(
        f":computer: {total_result[0]} / {total_result[1]} checks passed ({total_result[2]}%)\n"
    )
    # display all of the analysis results if verbose output is requested
    output.print_analysis_details(chasten_results_save, verbose=verbose)
    # save all of the results from this analysis
    saved_file_name = filesystem.write_chasten_results(
        output_directory, project, chasten_results_save, save
    )
    # output the name of the saved file if saving successfully took place
    if saved_file_name:
        output.console.print(f":sparkles: Saved the file '{saved_file_name}'")
    # confirm whether or not all of the checks passed
    # and then display the appropriate diagnostic message
    all_checks_passed = all(check_status_list)
    end_time = time.time()
    elapsed_time = end_time - start_time

    if not all_checks_passed:
        output.console.print(":sweat: At least one check did not pass.")
        if store_result:
            # writes results of analyze into a markdown file
            analysis_file_dir.write_text(analysis_result, encoding="utf-8")
            output.console.print(
                f"\n:sparkles: Results saved in: {os.path.abspath(analysis_file_dir)}\n"
            )
        sys.exit(constants.markers.Non_Zero_Exit)
    output.console.print(
        f"\n:joy: All checks passed. Elapsed Time: {elapsed_time} seconds"
    )
    output.logger.debug("Analysis complete.")
    if store_result:
        # writes results of analyze into a markdown file
        result_path = os.path.abspath(analysis_file_dir)
        analysis_file_dir.write_text(analysis_result, encoding="utf-8")
        output.console.print(f"\n:sparkles: Results saved in: {result_path}\n")
        if display:
            database.display_results_frog_mouth(result_path, util.get_OS())


@cli.command()
def integrate(  # noqa: PLR0913
    project: str = typer.Argument(help="Name of the project."),
    json_path: List[Path] = typer.Argument(
        help="Directories, files, or globs for chasten's JSON result file(s).",
    ),
    output_directory: Path = typer.Option(
        ...,
        "--save-directory",
        "-s",
        help="A directory for saving converted file(s).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    debug_level: debug.DebugLevel = typer.Option(
        debug.DebugLevel.ERROR.value,
        "--debug-level",
        "-l",
        help="Specify the level of debugging output.",
    ),
    debug_destination: debug.DebugDestination = typer.Option(
        debug.DebugDestination.CONSOLE.value,
        "--debug-dest",
        "-t",
        help="Specify the destination for debugging output.",
    ),
    force: bool = typer.Option(
        False,
        help="Create converted results files even if they exist",
    ),
    verbose: bool = typer.Option(False, help="Display verbose debugging output"),
) -> None:
    """🚧 Integrate files and make a database."""
    # output the preamble, including extra parameters specific to this function
    output_preamble(
        verbose,
        debug_level,
        debug_destination,
        project=project,
        output_directory=output_directory,
        json_path=json_path,
        force=force,
    )
    output.logger.debug("Integrate function started.")
    # output the list of directories subject to checking
    output.console.print()
    output.console.print(":sparkles: Combining data file(s) in:")
    output.logger.debug(":sparkles: Combining data file(s) in:")
    output.console.print()
    output.print_list_contents(json_path)
    # extract all of the JSON dictionaries from the specified files
    json_dicts = filesystem.get_json_results(json_path)
    count = len(json_path)
    output.console.print(f"\n:sparkles: Total of {count} files in all directories.")
    # combine all of the dictionaries into a single string
    combined_json_dict = process.combine_dicts(json_dicts)
    # write the combined JSON file string to the filesystem
    combined_json_file_name = filesystem.write_dict_results(
        combined_json_dict, output_directory, project
    )
    # output the name of the saved file if saving successfully took place
    if combined_json_file_name:
        output.console.print(f"\n:sparkles: Saved the file '{combined_json_file_name}'")
        output.logger.debug(f"Saved the file '{combined_json_file_name}'.")
    # "flatten" (i.e., "un-nest") the now-saved combined JSON file using flatterer
    # create the SQLite3 database and then configure the database for use in datasette
    combined_flattened_directory = filesystem.write_flattened_csv_and_database(
        combined_json_file_name,
        output_directory,
        project,
    )
    output.logger.debug("Flattened JSON and created SQLite database.")
    # output the name of the saved file if saving successfully took place
    if combined_flattened_directory:
        output.console.print(
            f"\n:sparkles: Created this directory structure in {Path(combined_flattened_directory).parent}:"
        )
        combined_directory_tree = filesystem.create_directory_tree_visualization(
            Path(combined_flattened_directory)
        )
        output.console.print()
        output.console.print(combined_directory_tree)
        output.logger.debug("Integrate function completed successfully.")


@cli.command()
def datasette_serve(  # noqa: PLR0913
    database_path: Path = typer.Argument(
        help="SQLite3 database file storing chasten's results.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    port: int = typer.Option(
        8001,
        "--port",
        "-p",
        help="Port on which to run a datasette instance",
    ),
    metadata: Path = typer.Option(
        None,
        "--metadata",
        "-m",
        help="Meta-data file storing database configuration.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    debug_level: debug.DebugLevel = typer.Option(
        debug.DebugLevel.ERROR.value,
        "--debug-level",
        "-l",
        help="Specify the level of debugging output.",
    ),
    debug_destination: debug.DebugDestination = typer.Option(
        debug.DebugDestination.CONSOLE.value,
        "--debug-dest",
        "-t",
        help="Specify the destination for debugging output.",
    ),
    verbose: bool = typer.Option(False, help="Display verbose debugging output"),
) -> None:
    """🏃 Start a local datasette server."""
    # output the preamble, including extra parameters specific to this function
    output_preamble(
        verbose,
        debug_level,
        debug_destination,
        database=database_path,
        datasette_port=port,
        metadata=metadata,
    )
    # setup the console and the logger through the output module
    output.setup(debug_level, debug_destination)
    output.logger.debug(f"Display verbose output? {verbose}")
    output.logger.debug(f"Debug level? {debug_level.value}")
    output.logger.debug(f"Debug destination? {debug_destination.value}")
    # display diagnostic information about the datasette instance
    label = ":sparkles: Starting a local datasette instance:"
    display_serve_or_publish_details(
        label, database_path, metadata, port, publish=False
    )
    # start the datasette server that will run indefinitely;
    # shutting down the datasette server with a CTRL-C will
    # also shut down this command in chasten
    database.start_datasette_server(
        database_path=database_path,
        datasette_port=port,
        datasette_metadata=metadata,
        publish=False,
        OpSystem=util.get_OS(),
    )


@cli.command()
def datasette_publish(  # noqa: PLR0913
    database_path: Path = typer.Argument(
        help="SQLite3 database file storing chasten's results.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    metadata: Path = typer.Option(
        None,
        "--metadata",
        "-m",
        help="Meta-data file storing database configuration.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
    datasette_platform: enumerations.DatasettePublicationPlatform = typer.Option(
        enumerations.DatasettePublicationPlatform.FLY.value,
        "--platform",
        "-p",
        help="Specify the deployment platform for datasette.",
    ),
    debug_level: debug.DebugLevel = typer.Option(
        debug.DebugLevel.ERROR.value,
        "--debug-level",
        "-l",
        help="Specify the level of debugging output.",
    ),
    debug_destination: debug.DebugDestination = typer.Option(
        debug.DebugDestination.CONSOLE.value,
        "--debug-dest",
        "-t",
        help="Specify the destination for debugging output.",
    ),
    verbose: bool = typer.Option(False, help="Display verbose debugging output"),
) -> None:
    """🌎 Publish a datasette to Fly or Vercel."""
    # output the preamble, including extra parameters specific to this function
    output_preamble(
        verbose,
        debug_level,
        debug_destination,
        database=database_path,
        metadata=metadata,
    )
    # setup the console and the logger through the output module
    output.setup(debug_level, debug_destination)
    output.logger.debug(f"Display verbose output? {verbose}")
    output.logger.debug(f"Debug level? {debug_level.value}")
    output.logger.debug(f"Debug destination? {debug_destination.value}")
    output.console.print()
    output.console.print(
        f":wave: Make sure that you have previously logged into the '{datasette_platform.value}' platform"
    )
    # display details about the publishing step
    label = f":sparkles: Publishing a datasette to {datasette_platform.value}:"
    display_serve_or_publish_details(label, database_path, metadata, publish=True)
    # publish the datasette instance using fly.io;
    # this passes control to datasette and then to
    # the fly program that must be installed
    database.start_datasette_server(
        database_path=database_path,
        datasette_metadata=metadata,
        datasette_platform=datasette_platform.value,
        publish=True,
        OpSystem=util.get_OS(),
    )


@cli.command()
def log() -> None:
    """🦚 Start the logging server."""
    # display the header
    output.print_header()
    # display details about the server
    output.print_server()
    # run the server; note that this
    # syslog server receives debugging
    # information from chasten.
    # It must be started in a separate process
    # before running any sub-command
    # of the chasten tool
    server.start_syslog_server()


@cli.command()
def version():
    """🖥️  Display the version of Chasten."""
    # Get Chasten version from util file
    version_string = util.get_chasten_version()
    # output chasten version
    typer.echo(f"chasten {version_string}")


# ---
# End region: Command-line interface functions }}}
# ---
