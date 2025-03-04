# Infinite-Fusion-Soul-Manager (IFSM)

## Description
Infinite Fusion Soul Manager or IFSM, is an open-source tool for the fan-made Pokemon game - Infinite Fusion. This tool aims to help alleviate the tediousness and time consuming process of keeping track of Pokemon caught during a playthrough of the game, especially when using Soul Link Nuzlocke rules. If you have ever done a Soul Link Nuzlocke playthrough of this game with 2+ people, you have likely spent more than a few minutes either editing and viewing a homemade spreadsheet, or by streaming your game over a VC app like Discord while trying to figure out which pokemon are liked to what and therefore what fusions can be made with your chosen ruleset. This tool acts as an advanced spreadsheet that allows you to easily add, remove, evolve, fuse and view all parties' Pokemon. You can also easily preview all available fusions for each player.

## How to Use

### Register and Login
First thing you will need to do is register with a username and password. As this tool uses a Database to store all the pokemon info for each user and their playthroughs, a login is required to use this tool. There are no restrictions on what your username and password can be but just make sure to use best practices when creating both. Make sure you remember your username and password as there is no way to recover your account since an email is not required.

### Creating a Session
After you login with your registered username and password, you will be directed to a "Create Session" page. Here you just put in the preliminary info for your session which includes how many players, each player's name and what premade ruleset you would like to use if you so choose. Once all settings are chosen you can continue to the session manager and start adding Pokemon. Each user can create and save up to three (3) sessions at a time. If you want to create another session, you will need to delete one that is currently saved.

#### Rulesets
The premade rulesets are what I think are the most common rulesets when playing a Soul Link Nuzlocke of this game. By selecting and using one of the rulesets other than 'Ruleset 1', this tool will automatically link Pokemon caught on the same route, keep track of number of encounters, allow the user to preview any valid combinations of fusions and more depending on which ruleset is chosen. Anyone is allowed to play however they feel is best for them, and in fact I strongly encourage this (if you plan on using this tool for your playthrough, don't feel like you need to use one of the rulesets listed, always play how you want to play), but I wanted to make sure that this tool takes a lot of the busywork out of managing a spreadsheet. If you don't see your particular ruleset listed just select 'Ruleset 1'. While you won't be able to reap the full benefits of the tool, I imagine it will still be a lot easier than using something like Google sheets or Excel. I apologize if your specific ruleset that you like to play with isn't listed, but unfortunately I cannot account for everyone's specific tastes. At the very least I decided to make sure that I got what I thought are the most common rulesets.

### Using the Manager
From the "Session Manager" page you can add, faint, revive, delete, fuse, preview fusions, evolve, switch in/out of party/box, swap fusions and even change sprite pictures to ones in game.

#### Adding Pokemon
If not already shown, click on the accordian "Add Pokemon Section" to show the form for adding Pokemon. There will be a number of boxes equal to the number of players for the session. Add a Pokemon for each of the players. If your selected ruleset for session is not 'Ruleset 1', select the route that the pokemon were caught. Then click 'Add Pokemon' button to add them to the 'Box' Section.

#### Fainting Pokemon
If a Pokemon faints in battle, you can click the 'Faint' button to send it to the 'Fainted' section. Depending on the ruleset, one or more other Pokemon that are Soul-linked to fainted Pokemon may also be sent to the fainted section.

#### Revive or Delete Pokemon
In the 'Fainted' section, you have the option to revive or delete and fainted pokemon from the session. During a Nuzlocke playthrough generally Pokemon cannot be revived, however you may play with a ruleset of you own that allows for revives. This is also useful in case you accidentally faint a Pokemon that wasn't meant to be fainted yet. Simply click the 'Revive' button and that Pokemon as well as any Pokemon linked to it will be put back in the box in the state that it was fainted in. 

You can also delete any pokemon from the session from here as well. You are free to keep the Pokemon that are fainted here to have a complete history of all pokemon caught in the playthrough, or you can delete them as well. Unlike reviving pokemon you will need to delete each one individually. Just click on the 'Delete' button for the pokemon you wish to delete and 'OK' to confirm the deletion.

#### Fusing Pokemon
Fusing Pokemon is done through the 'Fuse Pokemon' accordian section. Click on the section to dropdown the form used to fuse pokemon if not already done. From here you can select the Pokemon that you wish to fuse together. After all boxes are filled click the 'Fuse Pokemon' button to complete the Fusion. If your selected ruleset does not allow that specific fusion to take place there will be an error and it will ask to you please select a valid fusion.

#### Preview Fusions
If a Pokemon is unfused, and are not playing with 'Ruleset 1' you have the option to preview all possible fusions for a Pokemon. When you click on the 'Preview Fusions' button it will take you to a separate page that shows all possible fusions for you and your partners depending on what ruleset you are playing on. The page will show each possible fusion as well as their base stats. You can also toggle the 'Show Final Evolutions of Fusions' to show the sprites, typing and base stats of the final evolution for all possible fusions. Note that even though some pokemon may have more than one 'final' evolution, e.g. Eevee or Poliwag, only one is coded to be the final evolution. Eevee for example has Sylveon coded as its final evolution. In these niche cases, it might be better to use another site to see all possible evolutions.

(WIP) In the future I would like to add a way to evolve pokemon from this page by selecting the sprites however, this will be something that needs to be implemented later. For now, unfortunately you will need to go back to previous page or click "View Current Session" on the top of the page and fuse them like it was explained in the previous "Fusing Pokemon" section above.

#### Evolving Pokemon
You can evolve Pokemon that are in your party or box by selected the evolution from the dropdown box labeled 'Evolve to...' and clicking the 'Evolve' button next to it. When selecting a pokemon form the dropdown box, you will see a list of all possible evolutions. This means you can skip evolutions if you would like or go to a preview evolution. If the pokemon is a fused pokemon, a list of all possible evolutions for that fusion. That means if you fused an Eevee with an Eevee, you will see 81 different evolutions to choose from.

#### Switching Pokemon In/Out of Party/Box
If you would like to have pokemon in your party you can add Pokemon to your party from the box by using the 'Switch with Party...' dropdown and 'To Party' button. If there is space in your party, i.e. you have less than six (6) pokemon in the party, you can click the 'To Party' button when either 'Switch with Party...' or 'Add to Party' is shown. If you try to add a pokemon to the party when you have six (6) pokemon already in the party, you will need to select a Pokemon from the dropdown box or you will get an error saying that the party is already full. When adding or switching out pokemon in the party, depending on your ruleset any soul-linked pokemon will also be automatically added or taken out of the party as well. 

You can also to the opposite and send pokemon to the box from the party section as well.

#### Swapping Fusions
If you want to switch the head and body of a fusion either because you used a DNA swapper or because you made a mistake fusing the pokemon, you can click the 'Swap Fusion' button under any fused pokemon, and the tool will swap the head and body of that pokemon only. Any soul-linked pokemon will not be affected.

#### Changing Sprites
This tool also allows you to change the sprite that you see within the tool so you can match it up with the sprite you have in game. Just select the variant from the 'Sprite Variants' dropdown box that you would like to see and click 'Switch' to change the sprite.

(WIP) I would like to have the tool show a preview of the sprite when hovering over the variant in the dropdown box in the future, however I will have to evaluate whether or not it is worth it to do so based on difficulty implementing as well as the affect on speed of the page. For now, since you can always just change the sprite whenever you want, you will just need to swap through all the sprites to 'preview' them.

#### More Pokemon information
If you would like to see more information for each Pokemon like abilities or stats, there is a link to FusionDex provided under each pokemon in your party and box.

### Changing Session
If you want to change to a different saved session, just click the 'Change Session' tab at the top of the page to take you to a Select Session page where you can select a new session to view.